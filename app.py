"""CineVault - Video library application entry point."""

import os
import logging

from flask import Flask, jsonify, render_template, request
from flask_session import Session

from config import Config
from services.db_service import init_database, init_db_pool

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Configure server-side sessions
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./sessions"
app.config["SESSION_PERMANENT"] = False
Session(app)

# Ensure required directories exist
for d in ["thumbnails", "sessions", "static/css", "static/js", "cache"]:
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


# Global error handlers
@app.errorhandler(404)
def not_found(e):
    if request.accept_mimetypes.accept_json:
        return jsonify({"error": "Not found"}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    if request.accept_mimetypes.accept_json:
        return jsonify({"error": "Internal server error"}), 500
    return render_template("500.html"), 500


# Health check endpoint
@app.route("/health")
def health_check():
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=55300, threads=8, send_bytes=2097152)
