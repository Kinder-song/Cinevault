"""Tags routes for CineVault. Uses TagRepository for all SQL.

NOTE: Both endpoints are admin-only. The `videos` table has no `user_id`
column, so we can't scope per-user at the SQL level — restrict to admin
instead.
"""

from flask import Blueprint, jsonify, request, session

from repositories.tag_repo import TagRepository
from repositories.video_repo import VideoRepository
from services.db_service import with_db_cursor
from utils.logger import video_logger
from routes.auth import login_required, admin_required

tags_bp = Blueprint('tags', __name__, url_prefix='/api/video')


@tags_bp.route('/<path:filename>/tags', methods=['POST'])
@login_required
@admin_required
def add_tag(filename):
    """Add a tag to a video."""
    data = request.get_json()
    tag_name = data.get('tag', '').strip()
    if not tag_name:
        return jsonify({'error': 'Tag name required'}), 400

    try:
        with with_db_cursor() as cursor:
            videos = VideoRepository(cursor)
            tags = TagRepository(cursor)

            video = videos.get_by_filename(filename)
            if not video:
                # Create a placeholder video record
                video_id = videos.insert(
                    filename=filename,
                    title=filename.rsplit('.', 1)[0],
                    file_size=0,
                    file_mtime=0,
                    duration=0,
                    width=0,
                    height=0,
                    codec='',
                    bitrate=0,
                    fps=0,
                )
            else:
                video_id = video['id']

            tag_id = tags.get_or_create_tag(tag_name)
            tags.attach_tag(video_id=video_id, tag_id=tag_id)

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error adding tag to video {filename}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@tags_bp.route('/<path:filename>/tags/<tag_name>', methods=['DELETE'])
@login_required
@admin_required
def remove_tag(filename, tag_name):
    """Remove a tag from a video."""
    try:
        with with_db_cursor() as cursor:
            # NOTE: videos table has no user_id column, so authorization
            # is enforced at the route level via @admin_required.
            TagRepository(cursor).detach_tag_by_name(filename, tag_name)

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error removing tag from video {filename}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
