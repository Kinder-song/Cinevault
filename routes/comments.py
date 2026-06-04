"""Comments routes."""
from flask import Blueprint, jsonify, request, session

from repositories import comment_repo as _comment_repo_module
from repositories.comment_repo import CommentRepository
from repositories.video_repo import VideoRepository
from services.db_service import with_db_cursor
from utils.logger import video_logger
from routes.auth import login_required, admin_required

comments_bp = Blueprint("comments", __name__, url_prefix="/api")


@comments_bp.route("/video/<path:filename>/comments", methods=["GET"])
@login_required
def list_comments(filename):
    try:
        with with_db_cursor() as cursor:
            videos = VideoRepository(cursor)
            comments = CommentRepository(cursor)
            video = videos.get_by_filename(filename)
            if not video:
                return jsonify({"comments": []})
            rows = comments.list_for_video(video["id"])
        return jsonify({"comments": rows})
    except Exception as e:
        video_logger.error("Error listing comments for %s: %s", filename, e)
        return jsonify({"error": "Internal server error"}), 500


@comments_bp.route("/video/<path:filename>/comments", methods=["POST"])
@login_required
def post_comment(filename):
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    if len(content) > _comment_repo_module.CommentRepository.MAX_CONTENT_LENGTH:
        return jsonify({"error": "content too long"}), 400
    try:
        with with_db_cursor() as cursor:
            videos = VideoRepository(cursor)
            comments = CommentRepository(cursor)
            video = videos.get_by_filename(filename)
            if not video:
                return jsonify({"error": "Video not found"}), 404
            cid = comments.add(
                video_id=video["id"],
                user_id=session["user_id"],
                content=content,
            )
        return jsonify({"success": True, "id": cid})
    except Exception as e:
        video_logger.error("Error posting comment: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@comments_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@login_required
def delete_comment(comment_id):
    # Admins can delete any comment; users can only delete their own.
    is_admin = session.get("username") == "admin"
    try:
        with with_db_cursor() as cursor:
            comments = CommentRepository(cursor)
            if is_admin:
                cursor.execute(
                    "DELETE FROM comments WHERE id = %s", (comment_id,)
                )
                ok = cursor.rowcount > 0
            else:
                ok = comments.delete_owned(comment_id, session["user_id"])
        if not ok:
            return jsonify({"error": "Not found or not owned"}), 403 if not is_admin else 404
        return jsonify({"success": True})
    except Exception as e:
        video_logger.error("Error deleting comment: %s", e)
        return jsonify({"error": "Internal server error"}), 500
