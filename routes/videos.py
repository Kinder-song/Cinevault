"""Video routes for CineVault - all video-related endpoints."""

from functools import wraps
import os

import bcrypt
from flask import (
    Blueprint, jsonify, redirect, render_template, request,
    send_file, send_from_directory, session, Response
)

from services.db_service import get_db_connection, with_db_cursor
from services.sync_service import sync_and_get_videos, sync_video_to_db
from services.video_service import (
    VIDEO_MIME_TYPES, IMAGE_EXTENSIONS, SUBTITLE_EXTENSIONS,
    scan_subtitles, scan_screenshots, generate_thumbnail, video_dict_from_row
)
from utils.security import validate_video_path
from utils.formatters import format_duration, format_filesize, format_bitrate, format_fps
from utils.logger import video_logger

videos_bp = Blueprint('videos', __name__, url_prefix='/')


def login_required(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def get_user_video_path(user_id):
    """Get user's video path from session or database.

    Args:
        user_id: The user ID from session.

    Returns:
        The user's configured video path or default from config.
    """
    from config import Config

    # Try session cache first
    if 'video_path' in session:
        return session['video_path']

    with with_db_cursor() as cursor:
        if cursor is None:
            return Config.VIDEO_PATH
        cursor.execute("SELECT video_path FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        path = user['video_path'] if (user and user.get('video_path')) else Config.VIDEO_PATH
        session['video_path'] = path
        return path


# ==================== Index (paginated) ====================

@videos_bp.route('/')
@login_required
def index():
    """Video gallery page with server-side pagination."""
    from config import Config

    video_path = get_user_video_path(session['user_id'])
    db_rows = sync_and_get_videos(video_path)
    all_videos = [video_dict_from_row(r) for r in db_rows]

    # Server-side pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    per_page = min(max(per_page, 12), 96)  # clamp 12-96
    total = len(all_videos)
    total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
    page = min(max(page, 1), total_pages)
    start = (page - 1) * per_page
    videos = all_videos[start:start + per_page]

    # Get tags by video
    tags_by_video = {}
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT t.name, t.color, v.filename
                FROM tags t
                JOIN video_tags vt ON t.id = vt.tag_id
                JOIN videos v ON v.id = vt.video_id
            """)
            for row in cursor.fetchall():
                tags_by_video.setdefault(row['filename'], []).append({
                    'name': row['name'],
                    'color': row['color']
                })
    except Exception as e:
        video_logger.error(f"Error fetching tags: {e}")

    # Get collections for filter dropdown
    collections = []
    try:
        with with_db_cursor() as cursor:
            cursor.execute("SELECT id, name FROM collections ORDER BY name")
            collections = cursor.fetchall()
    except Exception as e:
        video_logger.error(f"Error fetching collections: {e}")

    return render_template('index.html',
                           videos=videos,
                           tags_by_video=tags_by_video,
                           page=page,
                           total_pages=total_pages,
                           per_page=per_page,
                           total=total,
                           collections=collections)


# ==================== Video Page ====================

@videos_bp.route('/video/')
@videos_bp.route('/video/<path:filename>')
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

    # Get subtitles
    subtitles = scan_subtitles(filename, video_path)

    # Get screenshots
    screenshots = scan_screenshots(filename, video_path)

    # Get tags from DB
    tags = []
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT t.name, t.color
                FROM tags t
                JOIN video_tags vt ON t.id = vt.tag_id
                JOIN videos v ON v.id = vt.video_id
                WHERE v.filename = %s
            """, (filename,))
            tags = cursor.fetchall()
    except Exception as e:
        video_logger.error(f"Error fetching tags for video {filename}: {e}")

    return render_template('video.html',
                           video=video,
                           tags=tags,
                           subtitles=subtitles,
                           screenshots=screenshots)


# ==================== Streaming ====================

@videos_bp.route('/stream/')
@videos_bp.route('/stream/<path:filename>')
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

@videos_bp.route('/thumbnail/')
@videos_bp.route('/thumbnail/<path:filename>')
@login_required
def thumbnail(filename=None):
    """Serve video thumbnails, generating if needed."""
    if not filename:
        return Response(status=404)

    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)

    if not os.path.exists(thumb_path):
        video_path = get_user_video_path(session['user_id'])
        fp = validate_video_path(video_path, filename)
        if fp and os.path.exists(fp):
            generate_thumbnail(os.path.splitext(filename)[0], fp)

    if os.path.exists(thumb_path):
        resp = send_file(thumb_path, mimetype='image/jpeg')
        resp.headers['Cache-Control'] = 'public, max-age=604800'
        return resp

    return Response(status=404)


# ==================== Subtitle ====================

@videos_bp.route('/subtitle/')
@videos_bp.route('/subtitle/<path:filename>')
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

@videos_bp.route('/screenshot/')
@videos_bp.route('/screenshot/<path:filename>')
@login_required
def serve_screenshot(filename=None):
    """Serve screenshot/image files."""
    if not filename:
        return "Not found", 404

    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, filename)
    if fp and os.path.exists(fp):
        return send_file(fp)

    # Also check thumbnails directory
    thumb_path = os.path.join('thumbnails', filename)
    if os.path.exists(thumb_path):
        return send_file(thumb_path)

    return "Not found", 404


# ==================== API: Video List ====================

@videos_bp.route('/api/videos', methods=['GET'])
@login_required
def api_videos():
    """Video list API with pagination, search, and sort."""
    video_path = get_user_video_path(session['user_id'])
    db_rows = sync_and_get_videos(video_path)
    all_videos = [video_dict_from_row(r) for r in db_rows]

    # Get tags
    tags_by_video = {}
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT t.name, t.color, v.filename
                FROM tags t
                JOIN video_tags vt ON t.id = vt.tag_id
                JOIN videos v ON v.id = vt.video_id
            """)
            for row in cursor.fetchall():
                tags_by_video.setdefault(row['filename'], []).append({
                    'name': row['name'],
                    'color': row['color']
                })
    except Exception as e:
        video_logger.error(f"Error fetching tags: {e}")

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    per_page = min(max(per_page, 12), 96)
    total = len(all_videos)
    total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
    page = min(max(page, 1), total_pages)
    start = (page - 1) * per_page

    # Search filter
    search = request.args.get('search', '').strip().lower()
    if search:
        all_videos = [v for v in all_videos if search in v.get('title', '').lower()
                      or search in v.get('filename', '').lower()]

    # Sort
    sort = request.args.get('sort', 'filename')
    reverse = request.args.get('order', 'asc') == 'desc'
    valid_sorts = ['filename', 'title', 'duration', 'size_bytes', 'created_at']
    if sort not in valid_sorts:
        sort = 'filename'
    try:
        all_videos.sort(key=lambda x: (x.get(sort) or '') if isinstance(x.get(sort), str) else (x.get(sort) or 0), reverse=reverse)
    except Exception:
        pass

    # Paginate after filtering
    total = len(all_videos)
    start = min(start, total - 1) if total > 0 else 0
    videos = all_videos[start:start + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1

    return jsonify({
        'videos': videos,
        'tags': tags_by_video,
        'total': total,
        'page': page,
        'total_pages': total_pages
    })


# ==================== API: Video Data ====================

@videos_bp.route('/api/video/<path:filename>/data', methods=['GET'])
@login_required
def get_video_data(filename):
    """Return complete video data for playlist switching."""
    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, filename)
    if not fp:
        return jsonify({'error': 'Not found', 'reason': 'path validation failed'}), 404
    if not os.path.exists(fp):
        return jsonify({'error': 'Not found', 'reason': 'file not found'}), 404

    row = sync_video_to_db(filename, fp)
    if not row:
        return jsonify({'error': 'Not found', 'reason': 'db sync failed'}), 404

    video = video_dict_from_row(row)

    # Subtitles
    subtitles = scan_subtitles(filename, video_path)

    # Screenshots
    screenshots = scan_screenshots(filename, video_path)

    # Tags
    tags = []
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT t.name, t.color
                FROM tags t
                JOIN video_tags vt ON t.id = vt.tag_id
                JOIN videos v ON v.id = vt.video_id
                WHERE v.filename = %s
            """, (filename,))
            tags = cursor.fetchall()
    except Exception as e:
        video_logger.error(f"Error fetching tags for video {filename}: {e}")

    return jsonify({
        'video': video,
        'subtitles': subtitles,
        'screenshots': screenshots,
        'tags': tags
    })


# ==================== API: Progress ====================

@videos_bp.route('/api/video/<path:filename>/progress', methods=['POST'])
@login_required
def save_progress(filename):
    """Save watch progress for a video."""
    data = request.get_json()
    progress = data.get('progress', 0)

    try:
        with with_db_cursor() as cursor:
            cursor.execute(
                "UPDATE videos SET watched_duration = %s WHERE filename = %s",
                (int(progress), filename)
            )
        return jsonify({'success': True})
    except Exception as e:
        video_logger.error(f"Error saving progress for {filename}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: Favorite ====================

@videos_bp.route('/api/video/<path:filename>/favorite', methods=['POST'])
@login_required
def toggle_favorite(filename):
    """Toggle favorite status for a video."""
    data = request.get_json()
    val = 1 if data.get('is_favorite') else 0

    try:
        with with_db_cursor() as cursor:
            cursor.execute(
                "UPDATE videos SET favorite = %s WHERE filename = %s",
                (val, filename)
            )
        return jsonify({'success': True})
    except Exception as e:
        video_logger.error(f"Error toggling favorite for {filename}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: Rating ====================

@videos_bp.route('/api/video/<path:filename>/rating', methods=['POST'])
@login_required
def set_rating(filename):
    """Set rating (0-5) for a video."""
    data = request.get_json()
    rating = max(0, min(5, int(data.get('rating', 0))))

    try:
        with with_db_cursor() as cursor:
            cursor.execute(
                "UPDATE videos SET rating = %s WHERE filename = %s",
                (rating, filename)
            )
        return jsonify({'success': True})
    except Exception as e:
        video_logger.error(f"Error setting rating for {filename}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== API: Refresh Thumbnail ====================

@videos_bp.route('/api/video/<path:filename>/refresh-thumb', methods=['POST'])
@login_required
def refresh_thumbnail(filename):
    """Refresh/regenerate video thumbnail."""
    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, filename)
    if not fp:
        return jsonify({'success': False, 'error': 'Invalid path'}), 400

    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    new_thumb = generate_thumbnail(os.path.splitext(filename)[0], fp)

    try:
        with with_db_cursor() as cursor:
            cursor.execute(
                "UPDATE videos SET thumbnail_path = %s WHERE filename = %s",
                (new_thumb or '', filename)
            )
    except Exception as e:
        video_logger.error(f"Error updating thumbnail path for {filename}: {e}")

    return jsonify({'success': bool(new_thumb), 'thumbnail': new_thumb})