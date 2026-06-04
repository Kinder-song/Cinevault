"""Authentication routes for CineVault."""

from functools import wraps

import bcrypt
from flask import Blueprint, jsonify, redirect, render_template, request, session

from services.db_service import get_db_connection
from utils.logger import auth_logger
from utils.security import LoginAttemptTracker

auth_bp = Blueprint('auth', __name__)

login_tracker = LoginAttemptTracker(max_attempts=5, lockout_seconds=300)


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


def admin_required(f):
    """Decorator to require the logged-in user to be 'admin'.

    Use as an *inner* decorator under @login_required so an unauthenticated
    request gets 401 first and a non-admin authenticated request gets 403:

        @blueprint.route(...)
        @login_required
        @admin_required
        def destructive_view():
            ...

    Why this exists: the `collections` and `videos` tables do not have a
    `user_id` column, so destructive endpoints on those resources can't
    scope by owner at the SQL level. Restricting to the admin user keeps
    the multi-tenant attack surface shut until a proper `user_id` schema
    is introduced.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('username') != 'admin':
            return jsonify({'error': 'Admin only'}), 403
        return f(*args, **kwargs)
    return decorated


def _get_client_ip():
    """Get client IP from request, considering X-Forwarded-For header."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login GET and POST requests."""
    if request.method == 'GET':
        return render_template('login.html')

    client_ip = _get_client_ip()

    if login_tracker.is_locked_out(client_ip):
        auth_logger.warning(f"Login attempt from locked out IP: {client_ip}")
        return jsonify({'error': 'Too many failed attempts. Please try again later.'}), 429

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    conn = get_db_connection()
    if not conn:
        auth_logger.error("Database connection failed during login")
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, password_hash, password_changed FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        login_tracker.record_success(client_ip)
        # Clear and reset session to prevent session fixation
        session.clear()
        session['user_id'] = user['id']
        session['username'] = username
        auth_logger.info(f"Successful login for user: {username}")

        # Check if user needs to change password (first login with default password)
        if not user.get('password_changed', False):
            return jsonify({'success': True, 'must_change_password': True})

        return jsonify({'success': True})

    remaining = login_tracker.record_failure(client_ip)
    auth_logger.warning(f"Failed login attempt for username: {username} from IP: {client_ip}")

    if remaining == 0:
        return jsonify({'error': 'Too many failed attempts. Please try again later.'}), 429

    return jsonify({'error': f'Invalid credentials. {remaining} attempts remaining.'}), 401


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to login."""
    username = session.get('username', 'unknown')
    session.clear()
    auth_logger.info(f"User logged out: {username}")
    return redirect('/login')