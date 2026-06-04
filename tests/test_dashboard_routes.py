"""Verify /dashboard route uses StatsRepository directly after the Plan 3
Task 6 refactor (the thin get_dashboard_stats wrapper was dropped)."""
from unittest.mock import patch
import pytest

from app import app, csrf


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # flask-seasurf 2.0 reads CSRF_DISABLE only at init_app() time, so
    # also flip the instance flag so it takes effect in this test.
    app.config["CSRF_DISABLE"] = True
    original = csrf._csrf_disable
    csrf._csrf_disable = True
    try:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
            yield c
    finally:
        csrf._csrf_disable = original


def test_dashboard_renders(client):
    """GET /dashboard returns 200 and calls all 4 StatsRepository methods."""
    with patch("routes.dashboard.StatsRepository") as Repo:
        repo = Repo.return_value
        repo.get_main_stats.return_value = {
            "total_videos": 5,
            "total_duration": 600.0,
            "total_size": 1024,
            "watched_duration": 100.0,
            "favorites": 2,
        }
        repo.get_tag_stats.return_value = [
            {"name": "action", "color": "#f00", "count": 3},
        ]
        repo.get_codec_stats.return_value = [
            {"codec": "h264", "count": 5},
        ]
        repo.get_resolution_stats.return_value = {
            "uhd": 0, "fhd": 3, "hd": 2, "sd": 0,
        }
        res = client.get("/dashboard")
        assert res.status_code == 200
        # The route should have called each of the 4 methods exactly once
        repo.get_main_stats.assert_called_once_with()
        repo.get_tag_stats.assert_called_once_with(limit=20)
        repo.get_codec_stats.assert_called_once_with()
        repo.get_resolution_stats.assert_called_once_with()


def test_dashboard_formats_durations_and_size(client):
    """The formatted fields used by dashboard.html must be populated from the
    StatsRepository output."""
    with patch("routes.dashboard.StatsRepository") as Repo:
        repo = Repo.return_value
        repo.get_main_stats.return_value = {
            "total_videos": 0,
            "total_duration": 3725.0,
            "total_size": 5_242_880,
            "watched_duration": 60.0,
            "favorites": 0,
        }
        repo.get_tag_stats.return_value = []
        repo.get_codec_stats.return_value = []
        repo.get_resolution_stats.return_value = {
            "uhd": 0, "fhd": 0, "hd": 0, "sd": 0,
        }
        res = client.get("/dashboard")
        assert res.status_code == 200
        # Render with a known user to keep login_required happy
        body = res.get_data(as_text=True)
        # 3725 seconds -> 1:02:05
        assert "1:02:05" in body
        # 5_242_880 bytes -> 5.0 MB (format_filesize)
        assert "5.0 MB" in body
