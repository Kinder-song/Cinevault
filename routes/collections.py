"""Collections routes for CineVault.

NOTE: The `collections` table in the live database does NOT have a `user_id`
column, so we cannot scope queries to a user at the SQL level.

Authorization policy:
  - GET (list, detail)        — any logged-in user
  - POST/DELETE (mutations)   — admin only (@admin_required)

This keeps the IDOR window shut until the schema gains a proper user_id
column (or a collection_members join table).
"""

import os

from flask import Blueprint, jsonify, request, session

from repositories.collection_repo import CollectionRepository
from repositories.video_repo import VideoRepository
from services.db_service import with_db_cursor
from services.video_service import video_dict_from_row
from utils.logger import video_logger
from utils.security import validate_video_path
from routes.auth import login_required, admin_required
from routes.videos import get_user_video_path

collections_bp = Blueprint('collections', __name__, url_prefix='/api/collections')


@collections_bp.route('', methods=['GET'])
@login_required
def list_collections():
    """List all collections with video count."""
    try:
        with with_db_cursor() as cursor:
            collections = CollectionRepository(cursor).list_all()

        return jsonify({'collections': collections})

    except Exception as e:
        video_logger.error(f"Error listing collections: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@collections_bp.route('', methods=['POST'])
@login_required
@admin_required
def create_collection():
    """Create a new collection."""
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400

    description = data.get('description', '').strip()

    try:
        with with_db_cursor() as cursor:
            col_id = CollectionRepository(cursor).create(
                name=name, description=description
            )

        return jsonify({'success': True, 'id': col_id})

    except Exception as e:
        video_logger.error(f"Error creating collection: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@collections_bp.route('/<int:col_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_collection(col_id):
    """Delete a collection."""
    try:
        with with_db_cursor() as cursor:
            CollectionRepository(cursor).delete(collection_id=col_id)

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error deleting collection {col_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@collections_bp.route('/<int:col_id>/videos', methods=['POST'])
@login_required
@admin_required
def add_video_to_collection(col_id):
    """Add a video to a collection."""
    data = request.get_json()
    filename = data.get('filename', '').strip()
    if not filename:
        return jsonify({'error': 'Filename required'}), 400

    try:
        with with_db_cursor() as cursor:
            collections = CollectionRepository(cursor)
            videos_repo = VideoRepository(cursor)

            # Verify collection exists
            existing = collections.get_with_videos(collection_id=col_id)
            if not existing:
                return jsonify({'error': 'Collection not found'}), 404

            # Verify video exists in user's video_path
            video_path = get_user_video_path(session['user_id'])
            fp = validate_video_path(video_path, filename)
            if not fp or not os.path.exists(fp):
                return jsonify({'error': 'Video not found'}), 404

            # Get video id
            video = videos_repo.get_by_filename(filename)
            if not video:
                return jsonify({'error': 'Video not found'}), 404

            # Add to collection (repo swallows IntegrityError -> duplicate)
            collections.add_video(
                collection_id=col_id, video_id=video['id']
            )

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error adding video to collection {col_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@collections_bp.route('/<int:col_id>/videos/<path:filename>', methods=['DELETE'])
@login_required
@admin_required
def remove_video_from_collection(col_id, filename):
    """Remove a video from a collection."""
    try:
        with with_db_cursor() as cursor:
            collections = CollectionRepository(cursor)

            # Verify collection exists
            existing = collections.get_with_videos(collection_id=col_id)
            if not existing:
                return jsonify({'error': 'Collection not found'}), 404

            collections.remove_video(
                collection_id=col_id, filename=filename
            )

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error removing video from collection {col_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@collections_bp.route('/<int:col_id>', methods=['GET'])
@login_required
def get_collection(col_id):
    """Get a collection with its videos."""
    try:
        with with_db_cursor() as cursor:
            result = CollectionRepository(cursor).get_with_videos(
                collection_id=col_id
            )

            if not result:
                return jsonify({'error': 'Collection not found'}), 404

            result['videos'] = [video_dict_from_row(v) for v in result['videos']]

        return jsonify(result)

    except Exception as e:
        video_logger.error(f"Error getting collection {col_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
