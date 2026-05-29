"""User profile routes for CineVault."""

import bcrypt
from flask import Blueprint, jsonify, redirect, render_template, request, session

from services.db_service import get_db_connection, with_db_cursor
from utils.security import validate_video_path
from utils.logger import video_logger
from routes.auth import login_required

user_bp = Blueprint('user', __name__)


@user_bp.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile."""
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT id, username, video_path
                FROM users WHERE id = %s
            """, (session['user_id'],))
            user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify(user)

    except Exception as e:
        video_logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': str(e)}), 500


# Settings page route (no prefix, so it's at /settings)
@user_bp.route('/settings', methods=['GET'])
@user_bp.route('/settings/', methods=['GET'])
@login_required
def settings_page():
    """Render settings page."""
    try:
        with with_db_cursor() as cursor:
            cursor.execute("""
                SELECT id, username, video_path
                FROM users WHERE id = %s
            """, (session['user_id'],))
            user = cursor.fetchone()

        if not user:
            return redirect('/login')

        return render_template('settings.html', user=user)

    except Exception as e:
        video_logger.error(f"Error loading settings page: {e}")
        return redirect('/')


@user_bp.route('/api/user/profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile (username, password, video_path)."""
    data = request.get_json()
    user_id = session['user_id']

    try:
        with with_db_cursor() as cursor:
            updates = []
            params = []

            # Update username
            new_username = data.get('username', '').strip()
            if new_username:
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND id != %s",
                    (new_username, user_id)
                )
                if cursor.fetchone():
                    return jsonify({'error': 'Username already exists'}), 400
                updates.append("username = %s")
                params.append(new_username)
                session['username'] = new_username

            # Update password
            new_password = data.get('password', '').strip()
            if new_password:
                verify_password = data.get('verify_password', '').strip()
                if not verify_password:
                    return jsonify({'error': 'Current password required to change password'}), 400

                cursor.execute(
                    "SELECT password_hash FROM users WHERE id = %s",
                    (user_id,)
                )
                user = cursor.fetchone()
                if not bcrypt.checkpw(verify_password.encode(), user['password_hash'].encode()):
                    return jsonify({'error': 'Current password incorrect'}), 400

                updates.append("password_hash = %s")
                params.append(bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode())
                session.regenerate_id()

            # Update video_path
            new_video_path = data.get('video_path', '').strip()
            if new_video_path:
                if not validate_video_path(new_video_path, ''):
                    return jsonify({'error': 'Invalid video path'}), 400
                updates.append("video_path = %s")
                params.append(new_video_path)
                session['video_path'] = new_video_path

            # Apply updates
            if updates:
                params.append(user_id)
                cursor.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
                    params
                )

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': str(e)}), 500