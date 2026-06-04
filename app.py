"""CineVault - Video library application entry point."""

import os
import logging

from flask import Flask, jsonify, render_template, request
from flask_session import Session
from flask_seasurf import SeaSurf
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from services.db_service import init_database, init_db_pool
from utils.errors import handle_route_exception

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=Config.PROXY_FIX_DEPTH)

# Configure app
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['SESSION_TYPE'] = Config.SESSION_TYPE
app.config['SESSION_FILE_DIR'] = Config.SESSION_FILE_DIR
# SECURITY: keep CSRF on even when callers set TESTING=True (flask-seasurf
# auto-disables itself under TESTING; the test suite wants CSRF enforced
# regardless so tests can verify rejection).
app.config['WTF_CSRF_ENABLED'] = True
# Use X-CSRF-Token (the conventional name) instead of flask-seasurf's default
# X-CSRFToken. NOTE: if you put this app behind a reverse proxy, ensure the
# proxy does NOT normalize or strip custom headers (no underscore-to-hyphen
# rewriting). main.js sends exactly this string.
app.config['CSRF_HEADER_NAME'] = 'X-CSRF-Token'
Session(app)
csrf = SeaSurf(app)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Ensure required directories exist
for d in ["thumbnails", "sessions", "static/css", "static/js"]:
    os.makedirs(d, exist_ok=True)

# Initialize database
init_database()
init_db_pool()

# Register blueprints
from routes.auth import auth_bp
from routes.videos import videos_bp
from routes.tags import tags_bp
from routes.collections import collections_bp
from routes.share import share_bp
from routes.dashboard import dashboard_bp
from routes.user import user_bp

app.register_blueprint(auth_bp)
app.register_blueprint(videos_bp)
app.register_blueprint(tags_bp)
app.register_blueprint(collections_bp)
app.register_blueprint(share_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(user_bp)

# Start the background thumbnail worker
from services.thumbnail_worker import start_worker
start_worker()


# Global error handlers
@app.errorhandler(404)
def not_found(e):
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Not found"}), 404
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    """Handle CSRF failures (and any other 403) with a clean JSON/text body.

    flask-seasurf raises werkzeug.Forbidden; the catch-all Exception handler
    would otherwise convert it to a 500. Return the 403 verbatim so clients
    can detect CSRF failures.
    """
    description = getattr(e, "description", str(e))
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Forbidden", "reason": description}), 403
    return description, 403


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal error: %s", e)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Internal server error"}), 500
    return render_template("500.html"), 500


@app.errorhandler(Exception)
def handle_exception(e):
    return handle_route_exception(e, logger)


# Health check endpoint
@app.route("/health")
def health_check():
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=55300, threads=8, send_bytes=2097152)


# CSRF: only the login route is exempt (it establishes the session, so it
# can't carry a CSRF token yet). The share blueprint does NOT need exemption
# because:
#   - GET /share/<token> is a safe HTTP method, SeaSurf ignores it
#   - POST /api/video/<file>/share is auth'd and the JS auto-attaches the
#     token via main.js's fetch wrapper
for _view_func in app.view_functions.values():
    if _view_func.__module__ == "routes.auth":
        csrf.exempt(_view_func)
