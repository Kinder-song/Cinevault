"""Routes package for CineVault."""

from routes.auth import auth_bp, login_required
from routes.index import index_bp
from routes.player import player_bp
from routes.api_videos import api_videos_bp
from routes.tags import tags_bp
from routes.collections import collections_bp
from routes.share import share_bp
from routes.dashboard import dashboard_bp
from routes.user import user_bp

__all__ = [
    'auth_bp',
    'index_bp',
    'player_bp',
    'api_videos_bp',
    'tags_bp',
    'collections_bp',
    'share_bp',
    'dashboard_bp',
    'user_bp',
    'login_required',
]
