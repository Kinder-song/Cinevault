"""Tags routes for CineVault."""

from flask import Blueprint, jsonify, request, session

from services.db_service import get_db_connection, with_db_cursor
from utils.logger import video_logger
from routes.auth import login_required

tags_bp = Blueprint('tags', __name__, url_prefix='/api/video')


@tags_bp.route('/<path:filename>/tags', methods=['POST'])
@login_required
def add_tag(filename):
    """Add a tag to a video."""
    data = request.get_json()
    tag_name = data.get('tag', '').strip()
    if not tag_name:
        return jsonify({'error': 'Tag name required'}), 400

    try:
        with with_db_cursor() as cursor:
            # Get or create video
            cursor.execute("SELECT id FROM videos WHERE filename = %s", (filename,))
            video = cursor.fetchone()
            if not video:
                # Create video entry if it doesn't exist
                cursor.execute(
                    "INSERT INTO videos (user_id, title, filename, filepath) VALUES (%s, %s, %s, %s)",
                    (session['user_id'], filename.rsplit('.', 1)[0], filename, filename)
                )
                video_id = cursor.lastrowid
            else:
                video_id = video['id']

            # Get or create tag
            cursor.execute("SELECT id, color FROM tags WHERE name = %s", (tag_name,))
            tag = cursor.fetchone()
            if not tag:
                cursor.execute("INSERT INTO tags (name) VALUES (%s)", (tag_name,))
                tag_id = cursor.lastrowid
            else:
                tag_id = tag['id']

            # Link video to tag (ignore if already exists)
            try:
                cursor.execute(
                    "INSERT INTO video_tags (video_id, tag_id) VALUES (%s, %s)",
                    (video_id, tag_id)
                )
            except Exception:
                pass  # Already linked

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error adding tag to video {filename}: {e}")
        return jsonify({'error': str(e)}), 500


@tags_bp.route('/<path:filename>/tags/<tag_name>', methods=['DELETE'])
@login_required
def remove_tag(filename, tag_name):
    """Remove a tag from a video."""
    try:
        with with_db_cursor() as cursor:
            # Verify video belongs to current user before deleting tag
            cursor.execute("""
                DELETE vt FROM video_tags vt
                JOIN videos v ON v.id = vt.video_id
                JOIN tags t ON t.id = vt.tag_id
                WHERE v.filename = %s AND t.name = %s AND v.user_id = %s
            """, (filename, tag_name, session['user_id']))

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error removing tag from video {filename}: {e}")
        return jsonify({'error': str(e)}), 500