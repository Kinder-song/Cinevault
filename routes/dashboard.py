"""Dashboard routes for CineVault."""

from flask import Blueprint, render_template

from repositories.stats_repo import StatsRepository
from services.db_service import with_db_cursor
from utils.formatters import format_duration, format_filesize
from utils.logger import db_logger
from routes.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page with stats."""
    stats: dict = {
        "total_videos": 0,
        "total_duration": 0.0,
        "total_size": 0,
        "watched_duration": 0.0,
        "favorites": 0,
        "tag_stats": [],
        "codec_stats": [],
        "res_stats": {"uhd": 0, "fhd": 0, "hd": 0, "sd": 0},
    }

    try:
        with with_db_cursor() as cursor:
            repo = StatsRepository(cursor)
            stats.update(repo.get_main_stats())
            stats["tag_stats"] = repo.get_tag_stats(limit=20)
            stats["codec_stats"] = repo.get_codec_stats()
            stats["res_stats"] = repo.get_resolution_stats()
    except Exception as e:
        db_logger.error(f"Failed to get dashboard stats: {e}")

    # Format duration and size for display
    stats['total_duration_formatted'] = format_duration(int(stats['total_duration']))
    stats['total_size_formatted'] = format_filesize(stats['total_size'])
    stats['watched_duration_formatted'] = format_duration(int(stats['watched_duration']))

    return render_template('dashboard.html', stats=stats)
