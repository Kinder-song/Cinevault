"""Collections routes for CineVault."""

from flask import Blueprint, jsonify, request, session
import mysql.connector

from services.db_service import get_db_connection, with_db_cursor
from services.video_service import video_dict_from_row
from utils.logger import video_logger
from routes.auth import login_required

collections_bp = Blueprint('collections', __name__, url_prefix='/api/collections')


@collections_bp.route('', methods=['GET'])
@login_required
def list_collections():
    """List all collections with video count."""
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.name, c.description, c.created_at,
                       COUNT(cv.video_id) as video_count
                FROM collections c
                LEFT JOIN collection_videos cv ON c.id = cv.collection_id
                GROUP BY c.id
                ORDER BY c.name
            """)
            collections = cursor.fetchall()

        return jsonify({'collections': collections})

    except Exception as e:
        video_logger.error(f"Error listing collections: {e}")
        return jsonify({'error': str(e)}), 500


@collections_bp.route('', methods=['POST'])
@login_required
def create_collection():
    """Create a new collection."""
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400

    description = data.get('description', '').strip()

    try:
        with with_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO collections (user_id, name, description) VALUES (%s, %s, %s)",
                (session['user_id'], name, description)
            )
            col_id = cursor.lastrowid

        return jsonify({'success': True, 'id': col_id})

    except Exception as e:
        video_logger.error(f"Error creating collection: {e}")
        return jsonify({'error': str(e)}), 500


@collections_bp.route('/<int:col_id>', methods=['DELETE'])
@login_required
def delete_collection(col_id):
    """Delete a collection."""
    try:
        with with_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM collection_videos WHERE collection_id = %s",
                (col_id,)
            )
            cursor.execute(
                "DELETE FROM collections WHERE id = %s AND user_id = %s",
                (col_id, session['user_id'])
            )

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error deleting collection {col_id}: {e}")
        return jsonify({'error': str(e)}), 500


@collections_bp.route('/<int:col_id>/videos', methods=['POST'])
@login_required
def add_video_to_collection(col_id):
    """Add a video to a collection."""
    data = request.get_json()
    filename = data.get('filename', '').strip()
    if not filename:
        return jsonify({'error': 'Filename required'}), 400

    try:
        with with_db_cursor() as cursor:
            # Verify collection belongs to current user
            cursor.execute("SELECT id FROM collections WHERE id = %s AND user_id = %s",
                           (col_id, session['user_id']))
            if not cursor.fetchone():
                return jsonify({'error': 'Collection not found'}), 404

            # Get video id
            cursor.execute("SELECT id FROM videos WHERE filename = %s", (filename,))
            video = cursor.fetchone()
            if not video:
                return jsonify({'error': 'Video not found'}), 404

            # Add to collection
            try:
                cursor.execute(
                    "INSERT INTO collection_videos (collection_id, video_id) VALUES (%s, %s)",
                    (col_id, video['id'])
                )
            except mysql.connector.IntegrityError:
                pass  # Already in collection

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error adding video to collection {col_id}: {e}")
        return jsonify({'error': str(e)}), 500


@collections_bp.route('/<int:col_id>/videos/<path:filename>', methods=['DELETE'])
@login_required
def remove_video_from_collection(col_id, filename):
    """Remove a video from a collection."""
    try:
        with with_db_cursor() as cursor:
            # Verify collection belongs to current user
            cursor.execute("SELECT id FROM collections WHERE id = %s AND user_id = %s",
                           (col_id, session['user_id']))
            if not cursor.fetchone():
                return jsonify({'error': 'Collection not found'}), 404

            cursor.execute("""
                DELETE cv FROM collection_videos cv
                JOIN videos v ON v.id = cv.video_id
                WHERE cv.collection_id = %s AND v.filename = %s
            """, (col_id, filename))

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error removing video from collection {col_id}: {e}")
        return jsonify({'error': str(e)}), 500


@collections_bp.route('/<int:col_id>', methods=['GET'])
@login_required
def get_collection(col_id):
    """Get a collection with its videos."""
    try:
        with with_db_cursor() as cursor:
            # Get collection
            cursor.execute(
                "SELECT * FROM collections WHERE id = %s AND user_id = %s",
                (col_id, session['user_id'])
            )
            collection = cursor.fetchone()

            if not collection:
                return jsonify({'error': 'Collection not found'}), 404

            # Get videos in collection
            cursor.execute("""
                SELECT v.* FROM videos v
                JOIN collection_videos cv ON v.id = cv.video_id
                WHERE cv.collection_id = %s
                ORDER BY cv.position, v.filename
            """, (col_id,))
            videos = [video_dict_from_row(r) for r in cursor.fetchall()]

        return jsonify({'collection': collection, 'videos': videos})

    except Exception as e:
        video_logger.error(f"Error getting collection {col_id}: {e}")
        return jsonify({'error': str(e)}), 500