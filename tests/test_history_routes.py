"""Verify /history page renders and /api/video/.../progress records history.

After Plan 4 Task 5:
- GET /history returns 200 and lists recent watch history items.
- POST /api/video/<f>/progress calls HistoryRepository.record in addition
  to VideoRepository.update_progress.
"""
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


def test_history_page_renders(client):
    with patch("routes.history.HistoryRepository") as Repo:
        Repo.return_value.list_recent.return_value = [
            {"filename": "a.mp4", "title": "A",
             "watched_at": "2024-01-01", "watched_seconds": 120,
             "thumbnail_path": "thumbnails/a.jpg"}
        ]
        res = client.get("/history")
        assert res.status_code == 200
        assert b"a.mp4" in res.data


def test_progress_records_history(client):
    """Saving progress should also append to watch_history."""
    with patch("routes.api_videos.VideoRepository") as Vid, \
         patch("routes.api_videos.HistoryRepository") as Hist:
        Vid.return_value.get_by_filename.return_value = {"id": 5}
        res = client.post(
            "/api/video/a.mp4/progress",
            json={"progress": 120},
        )
        assert res.status_code == 200
        Hist.return_value.record.assert_called_once()
