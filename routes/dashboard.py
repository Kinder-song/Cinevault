"""Dashboard routes for CineVault."""

from flask import Blueprint, render_template, session

from services.db_service import get_dashboard_stats
from utils.formatters import format_duration, format_filesize
from routes.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page with stats."""
    # Get stats
    stats = get_dashboard_stats()

    # Format duration and size for display
    stats['total_duration_formatted'] = format_duration(int(stats['total_duration']))
    stats['total_size_formatted'] = format_filesize(stats['total_size'])
    stats['watched_duration_formatted'] = format_duration(int(stats['watched_duration']))

    return render_template('dashboard.html', stats=stats)