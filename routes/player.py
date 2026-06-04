"""Video player page, streaming, thumbnails, subtitles, screenshots.

This blueprint owns every URL that serves a *file* or renders the per-video
player template:
    /video/<filename>     — HTML player page
    /stream/<filename>    — byte-range capable streaming
    /thumbnail/<filename> — JPEG cover (auto-generated on demand)
    /subtitle/<filename>  — .srt/.vtt/.ass passthrough
    /screenshot/<file>    — sibling image inside the user's video dir

Also owns ``get_user_video_path()``, the canonical helper for resolving the
caller's configured video directory. It lives here (rather than in
``routes.index`` or ``routes.api_videos``) so the other two blueprints can
import a single source of truth.
"""

import base64
import os

from flask import (
    Blueprint, redirect, render_template, request,
    send_file, session, Response,
)

from config import Config
from repositories.tag_repo import TagRepository
from repositories.user_repo import UserRepository
from services.db_service import with_db_cursor
from services.sync_service import sync_video_to_db
from services.video_service import (
    VIDEO_MIME_TYPES,
    generate_thumbnail,
    scan_subtitles,
    scan_screenshots,
)
from utils.logger import video_logger
from utils.security import validate_video_path
from routes.auth import login_required

player_bp = Blueprint("player", __name__)


def get_user_video_path(user_id: int) -> str:
    """Resolve the per-user video directory, caching the result in session.

    Falls back to ``Config.VIDEO_PATH`` when the user has no override stored.
    A DB failure here propagates (rather than silently returning the default)
    so callers see the real problem instead of mysteriously serving the wrong
    directory.
    """
    if "video_path" in session:
        return session["video_path"]

    with with_db_cursor() as cursor:
        user = UserRepository(cursor).get_by_id(user_id)
    path = (user or {}).get("video_path") or Config.VIDEO_PATH
    session["video_path"] = path
    return path


# ==================== Video Page ====================

@player_bp.route('/video/')
@player_bp.route('/video/<path:filename>')
@login_required
def video_page(filename=None):
    """Video player page."""
    if not filename:
        return redirect('/')

    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, filename)
    if not fp or not os.path.exists(fp):
        return "Video not found", 404

    row = sync_video_to_db(filename, fp)
    if not row:
        return "Video not found", 404

    # sync_video_to_db already returns a processed video dict
    video = row

    subtitles = scan_subtitles(filename, video_path)
    screenshots = scan_screenshots(filename, video_path)

    tags = []
    try:
        with with_db_cursor() as cursor:
            tags = TagRepository(cursor).list_tags_for_video(filename)
    except Exception as e:
        video_logger.error(f"Error fetching tags for video {filename}: {e}")

    return render_template('video.html',
                           video=video,
                           tags=tags,
                           subtitles=subtitles,
                           screenshots=screenshots)


# ==================== Streaming ====================

@player_bp.route('/stream/')
@player_bp.route('/stream/<path:filename>')
@login_required
def stream_video(filename=None):
    """Video streaming with Range request support."""
    if not filename:
        return "Not found", 404

    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, filename)
    if not fp or not os.path.exists(fp):
        return "Video not found", 404

    file_size = os.stat(fp).st_size
    file_mtime = int(os.stat(fp).st_mtime)
    ext = os.path.splitext(filename)[1].lower()
    ct = VIDEO_MIME_TYPES.get(ext, 'video/mp4')
    BUF = 2 * 1024 * 1024  # 2MB I/O buffer

    range_header = request.headers.get('Range')
    if range_header:
        try:
            parts = range_header.replace('bytes=', '').split('-')
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                return "Range Not Satisfiable", 416
        except (ValueError, IndexError):
            return "Bad Range", 400

        length = end - start + 1
        f = open(fp, 'rb', buffering=BUF)
        f.seek(start)

        def gen_range():
            remaining = length
            try:
                while remaining > 0:
                    chunk = f.read(min(BUF, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
            finally:
                f.close()

        resp = Response(gen_range(), 206, direct_passthrough=True)
        resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        resp.headers['Content-Length'] = str(length)
    else:
        f = open(fp, 'rb', buffering=BUF)

        def gen_full():
            try:
                while True:
                    chunk = f.read(BUF)
                    if not chunk:
                        break
                    yield chunk
            finally:
                f.close()

        resp = Response(gen_full(), 200, direct_passthrough=True)
        resp.headers['Content-Length'] = str(file_size)

    resp.headers['Content-Type'] = ct
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Cache-Control'] = 'private, max-age=86400'
    resp.headers['ETag'] = f'"{file_mtime}-{file_size}"'
    return resp


# ==================== Thumbnail ====================

@player_bp.route('/thumbnail/')
@player_bp.route('/thumbnail/<path:filename>')
@login_required
def thumbnail(filename=None):
    """Serve video thumbnails, auto-generating on first request."""
    if not filename:
        return Response(status=404)

    safe_basename = os.path.splitext(os.path.basename(filename))[0]
    thumb_path = os.path.join(Config.THUMBNAIL_DIR, f"{safe_basename}.jpg")

    # Self-heal: if the cached file is missing for any reason, try to regenerate.
    if not os.path.exists(thumb_path):
        video_path = get_user_video_path(session['user_id'])
        fp = validate_video_path(video_path, filename)
        if fp and os.path.exists(fp):
            generate_thumbnail(safe_basename, fp)

    if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
        resp = send_file(thumb_path, mimetype='image/jpeg')
        resp.headers['Cache-Control'] = 'public, max-age=604800'
        return resp

    # Be honest: thumbnail is unavailable, return a 1x1 transparent GIF so
    # the <img> tag doesn't show a broken-image icon in the card grid.
    transparent_pixel = base64.b64decode(
        b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
    )
    resp = Response(transparent_pixel, mimetype='image/gif')
    resp.headers['Cache-Control'] = 'no-store'
    return resp


# ==================== Subtitle ====================

@player_bp.route('/subtitle/')
@player_bp.route('/subtitle/<path:filename>')
@login_required
def serve_subtitle(filename=None):
    """Serve subtitle files."""
    if not filename:
        return "Not found", 404

    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, filename)
    if not fp or not os.path.exists(fp):
        return "Not found", 404

    ext = os.path.splitext(filename)[1].lower()
    mt = {'srt': 'text/plain', 'vtt': 'text/vtt', 'ass': 'text/plain'}.get(ext[1:], 'text/plain')
    resp = send_file(fp, mimetype=mt)
    resp.headers['Cache-Control'] = 'public, max-age=604800'
    return resp


# ==================== Screenshots ====================

@player_bp.route('/screenshot/', defaults={'filename': None})
@player_bp.route('/screenshot/<path:filename>')
@login_required
def serve_screenshot(filename):
    """Serve a screenshot/image file, restricted to Config.THUMBNAIL_DIR.

    SECURITY: filenames are restricted to the basename (no path separators)
    and resolved with realpath to prevent symlink escape. The previous
    implementation's os.path.join('thumbnails', filename) fallback allowed
    path traversal (e.g. /screenshot/../app.py to read app source).
    """
    if not filename:
        return "Not found", 404

    # Reject any path separators or '..' components.
    if os.sep in filename or "/" in filename or ".." in filename.split(os.sep):
        return "Not found", 404

    # Only allow exact basename (defense in depth).
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        return "Not found", 404

    # First, try next-to-source-video location.
    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, safe_name)
    if fp and os.path.exists(fp):
        return send_file(fp)

    # Fallback: serve from the configured thumbnail directory, but only if
    # the resolved path is actually inside it (no symlink escape).
    thumb_path = os.path.join(Config.THUMBNAIL_DIR, safe_name)
    real_thumb_dir = os.path.realpath(Config.THUMBNAIL_DIR)
    real_thumb_file = os.path.realpath(thumb_path)
    if real_thumb_file.startswith(real_thumb_dir + os.sep) and os.path.exists(
        real_thumb_file
    ):
        return send_file(real_thumb_file)

    return "Not found", 404
