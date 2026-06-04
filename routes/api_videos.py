"""JSON API for the video list and per-video mutations.

Endpoints:
    GET  /api/videos                              — paginated, searchable list
    GET  /api/video/<filename>/data               — full payload for playlist switch
    POST /api/video/<filename>/progress           — save watched_duration
    POST /api/video/<filename>/favorite           — toggle favorite flag
    POST /api/video/<filename>/rating             — set 0..5 star rating
    POST /api/video/<filename>/refresh-thumb      — queue thumbnail regen (admin)
    GET  /api/sync/thumbnail-status/<job_id>      — poll a regen job
"""

import os

from flask import Blueprint, jsonify, request, session

from repositories.tag_repo import TagRepository
from repositories.video_repo import VideoRepository
from routes.auth import admin_required, login_required
from routes.player import get_user_video_path
from services.db_service import with_db_cursor
from services.sync_service import sync_and_get_videos, sync_video_to_db
from services.video_service import (
    scan_screenshots,
    scan_subtitles,
    video_dict_from_row,
)
from utils.logger import video_logger
from utils.security import validate_video_path

api_videos_bp = Blueprint("api_videos", __name__)


# ==================== API: Video List ====================

@api_videos_bp.route("/api/videos", methods=["GET"])
@login_required
def api_videos():
    """Video list API.

    Order of operations: filter -> sort -> paginate. This ensures pagination
    metadata (``page``, ``total``, ``total_pages``) reflects the post-filter
    result set, not the pre-filter one.
    """
    video_path = get_user_video_path(session["user_id"])
    all_videos = [
        video_dict_from_row(r) for r in sync_and_get_videos(video_path)
    ]

    tags_by_video: dict = {}
    try:
        with with_db_cursor() as cursor:
            tags_by_video = TagRepository(cursor).list_tags_by_video()
    except Exception as e:
        video_logger.error("Error fetching tags: %s", e)

    # 1. Filter (search)
    search = request.args.get("search", "").strip().lower()
    if search:
        all_videos = [
            v for v in all_videos
            if search in (v.get("title") or "").lower()
            or search in (v.get("filename") or "").lower()
        ]

    # 2. Sort
    sort = request.args.get("sort", "filename")
    reverse = request.args.get("order", "asc") == "desc"
    valid_sorts = {"filename", "title", "duration", "size_bytes", "created_at"}
    if sort not in valid_sorts:
        sort = "filename"

    def _key(v):
        val = v.get(sort) or 0
        if isinstance(val, str):
            return val.lower()
        return val

    try:
        all_videos.sort(key=_key, reverse=reverse)
    except TypeError:
        pass  # mixed types; best-effort

    # 3. Paginate (AFTER filter/sort).
    # Floor page at 1 but do NOT clamp at total_pages: out-of-range pages
    # legitimately return an empty slice (a common REST pattern). Total
    # and total_pages in the response still reflect the post-filter set.
    per_page = min(max(request.args.get("per_page", 24, type=int), 12), 96)
    total = len(all_videos)
    total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
    page = max(request.args.get("page", 1, type=int), 1)
    start = (page - 1) * per_page
    videos = all_videos[start:start + per_page]

    return jsonify({
        "videos": videos,
        "tags": tags_by_video,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "sort": sort,
    })


# ==================== API: Video Data ====================

@api_videos_bp.route('/api/video/<path:filename>/data', methods=['GET'])
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

    subtitles = scan_subtitles(filename, video_path)
    screenshots = scan_screenshots(filename, video_path)

    tags = []
    try:
        with with_db_cursor() as cursor:
            tags = TagRepository(cursor).list_tags_for_video(filename)
    except Exception as e:
        video_logger.error(f"Error fetching tags for video {filename}: {e}")

    return jsonify({
        'video': video,
        'subtitles': subtitles,
        'screenshots': screenshots,
        'tags': tags,
    })


# ==================== API: Progress ====================

@api_videos_bp.route('/api/video/<path:filename>/progress', methods=['POST'])
@login_required
def save_progress(filename):
    """Save watch progress for a video."""
    data = request.get_json(silent=True) or {}
    raw = data.get('progress', 0)
    try:
        progress = int(raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'progress must be an integer'}), 400
    if progress < 0 or progress > 86400:  # 1 day max
        return jsonify({'error': 'progress out of range'}), 400

    try:
        with with_db_cursor() as cursor:
            VideoRepository(cursor).update_progress(filename, progress)
        return jsonify({'success': True})
    except Exception as e:
        video_logger.error("Error saving progress for %s: %s", filename, e)
        return jsonify({'error': 'Internal server error'}), 500


# ==================== API: Favorite ====================

@api_videos_bp.route('/api/video/<path:filename>/favorite', methods=['POST'])
@login_required
def toggle_favorite(filename):
    """Toggle favorite status for a video."""
    data = request.get_json(silent=True) or {}
    is_favorite = bool(data.get('is_favorite'))

    try:
        with with_db_cursor() as cursor:
            VideoRepository(cursor).set_favorite(filename, is_favorite)
        return jsonify({'success': True})
    except Exception as e:
        video_logger.error("Error toggling favorite for %s: %s", filename, e)
        return jsonify({'error': 'Internal server error'}), 500


# ==================== API: Rating ====================

@api_videos_bp.route('/api/video/<path:filename>/rating', methods=['POST'])
@login_required
def set_rating(filename):
    """Set rating (0-5) for a video."""
    data = request.get_json(silent=True) or {}
    raw = data.get('rating', 0)
    try:
        rating = int(raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'rating must be an integer'}), 400

    try:
        with with_db_cursor() as cursor:
            VideoRepository(cursor).set_rating(filename, rating)
        return jsonify({'success': True})
    except Exception as e:
        video_logger.error("Error setting rating for %s: %s", filename, e)
        return jsonify({'error': 'Internal server error'}), 500


# ==================== API: Refresh Thumbnail ====================

@api_videos_bp.route('/api/video/<path:filename>/refresh-thumb', methods=['POST'])
@login_required
@admin_required
def refresh_thumbnail(filename):
    """Queue a thumbnail regeneration job. Returns immediately with job_id.

    Status is queried via ``GET /api/sync/thumbnail-status/<job_id>``.
    """
    from services.thumbnail_worker import submit_thumbnail_job
    video_path = get_user_video_path(session['user_id'])
    fp = validate_video_path(video_path, filename)
    if not fp:
        return jsonify({"success": False, "error": "Invalid path"}), 400
    if not os.path.exists(fp):
        return jsonify({"success": False, "error": "Video file not found"}), 404

    job_id = submit_thumbnail_job(fp)
    return jsonify({"success": True, "job_id": job_id, "status": "pending"})


@api_videos_bp.route('/api/sync/thumbnail-status/<job_id>', methods=['GET'])
@login_required
def thumbnail_status(job_id):
    """Get the status of a thumbnail regeneration job."""
    from services.thumbnail_worker import get_thumbnail_status
    return jsonify({"status": get_thumbnail_status(job_id)})
