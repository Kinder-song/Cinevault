"""Share routes for CineVault."""

import datetime
import secrets

from flask import Blueprint, jsonify, redirect, render_template, request, session

from services.db_service import get_db_connection, with_db_cursor
from services.video_service import video_dict_from_row
from utils.logger import video_logger
from routes.auth import login_required

share_bp = Blueprint('share', __name__)


@share_bp.route('/api/video/<path:filename>/share', methods=['POST'])
@login_required
def create_share_token(filename):
    """Create a share token for a video."""
    from services.sync_service import sync_video_to_db
    from utils.security import validate_video_path
    from config import Config

    video_path = session.get('video_path', Config.VIDEO_PATH)
    fp = validate_video_path(video_path, filename)

    if not fp:
        return jsonify({'error': 'Invalid video path'}), 400

    # Get video data to ensure it exists
    row = sync_video_to_db(filename, fp)
    if not row:
        return jsonify({'error': 'Video not found'}), 404

    # Generate token
    token = secrets.token_hex(16)

    # Parse and clamp expiry hours to [1, 168] (1 hour - 7 days)
    if request.is_json:
        try:
            hours = int(request.get_json().get('hours', 24))
        except (TypeError, ValueError):
            return jsonify({"error": "hours must be an integer"}), 400
    else:
        hours = 24
    if hours < 1 or hours > 168:
        return jsonify({"error": "hours must be between 1 and 168"}), 400

    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        hours=hours
    )

    try:
        with with_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO share_tokens (token, video_filename, expires_at) VALUES (%s, %s, %s)",
                (token, row['filename'], expires)
            )

        return jsonify({
            'success': True,
            'token': token,
            'url': f'/share/{token}',
            'expires': str(expires)
        })

    except Exception as e:
        video_logger.error(f"Error creating share token for {filename}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@share_bp.route('/share/<token>')
def shared_video(token):
    """Access a shared video (no login required)."""
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT st.*, v.filename, v.title, v.duration, v.file_size
                FROM share_tokens st
                JOIN videos v ON v.filename = st.video_filename
                WHERE st.token = %s
            """, (token,))
            share = cursor.fetchone()

        if not share:
            return "Invalid or expired share link", 404

        if share['expires_at'] and share['expires_at'] < datetime.datetime.now(
            datetime.timezone.utc
        ).replace(tzinfo=None):
            return "Share link has expired", 410

        video = video_dict_from_row(share)

        return render_template('shared.html',
                               video=video,
                               token=token,
                               title=share.get('title', share['filename']))

    except Exception as e:
        video_logger.error(f"Error accessing shared video with token {token}: {e}")
        return "Error loading shared video", 500