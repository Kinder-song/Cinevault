"""User profile routes for CineVault."""

import bcrypt
from flask import Blueprint, jsonify, redirect, render_template, request, session

from repositories.user_repo import UserRepository
from services.db_service import with_db_cursor
from utils.security import validate_video_path_against_roots
from utils.logger import video_logger
from routes.auth import login_required

user_bp = Blueprint('user', __name__)


@user_bp.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile."""
    try:
        with with_db_cursor() as cursor:
            user = UserRepository(cursor).get_by_id(session['user_id'])

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify(user)

    except Exception as e:
        video_logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Settings page route (no prefix, so it's at /settings)
@user_bp.route('/settings', methods=['GET'])
@user_bp.route('/settings/', methods=['GET'])
@login_required
def settings_page():
    """Render settings page."""
    try:
        with with_db_cursor() as cursor:
            user = UserRepository(cursor).get_by_id(session['user_id'])

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

    # Build kwargs to pass to UserRepository.update_profile
    update_kwargs: dict = {}
    password_updated = False

    try:
        with with_db_cursor() as cursor:
            users = UserRepository(cursor)

            # Update username
            new_username = data.get('username', '').strip()
            if new_username:
                if users.username_exists(new_username, exclude_id=user_id):
                    return jsonify({'error': 'Username already exists'}), 400
                update_kwargs['username'] = new_username
                session['username'] = new_username

            # Update password
            new_password = data.get('password', '').strip()
            if new_password:
                verify_password = data.get('verify_password', '').strip()
                if not verify_password:
                    return jsonify({'error': 'Current password required to change password'}), 400

                user = users.get_by_id(user_id)
                if not bcrypt.checkpw(verify_password.encode(), user['password_hash'].encode()):
                    return jsonify({'error': 'Current password incorrect'}), 400

                update_kwargs['password_hash'] = bcrypt.hashpw(
                    new_password.encode(), bcrypt.gensalt()
                ).decode()
                # Mark password as changed (user completed first-time password change)
                update_kwargs['password_changed'] = True
                password_updated = True

            # Update video_path — must be inside an allowed root
            new_video_path = data.get('video_path', '').strip()
            if new_video_path:
                validated = validate_video_path_against_roots(new_video_path)
                if not validated:
                    return jsonify({
                        'error': 'video_path must be an existing directory inside an allowed root'
                    }), 400
                update_kwargs['video_path'] = validated
                session['video_path'] = validated

            # Apply updates via the repository
            if update_kwargs:
                users.update_profile(user_id=user_id, **update_kwargs)

            if password_updated:
                # First-time password change: keep session and redirect to home
                # Subsequent changes: clear session and require re-login
                return jsonify({'success': True, 'password_changed': True})

        return jsonify({'success': True})

    except Exception as e:
        video_logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500
