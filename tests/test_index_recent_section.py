"""Verify the index page renders a 'Recently watched' section.

The home page should fetch a small set of recent watch-history entries
and render them as a horizontal rail of thumbnail cards near the top of
the page. This test patches the repository and asserts that:

* the route returns 200,
* a known recent filename appears in the rendered HTML (within the
  `/video/<filename|urlencode>` href on the recent card), and
* the repository is called with the current user's id and limit=6.
"""
from unittest.mock import patch

import pytest

from app import app, csrf


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # GET requests don't need CSRF, but flip the flag for consistency
    # with the rest of the route-test suite.
    app.config["CSRF_DISABLE"] = True
    original = csrf._csrf_disable
    csrf._csrf_disable = True
    try:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["video_path"] = "/tmp"
            yield c
    finally:
        csrf._csrf_disable = original


def test_index_shows_recent_history(client):
    """The home page renders recent history from HistoryRepository."""
    recent_rows = [
        {"filename": "recent1.mp4", "title": "Recent 1", "watched_at": "2024-01-01"},
        {"filename": "recent2.mp4", "title": "Recent 2", "watched_at": "2023-12-31"},
    ]
    with patch("routes.index.sync_and_get_videos") as sync, \
         patch("routes.index.with_db_cursor") as cursor, \
         patch("routes.index.HistoryRepository") as HistoryRepo:
        # No real videos in the gallery, so the grid is empty.
        sync.return_value = []
        # The view calls tag/collection repos first, then history; the
        # cursor's fetchall just needs to be safe to call.
        cursor.return_value.__enter__.return_value.fetchall.return_value = []
        history_repo = HistoryRepo.return_value
        history_repo.list_recent.return_value = recent_rows

        res = client.get("/")

        assert res.status_code == 200
        assert b"recent1.mp4" in res.data
        history_repo.list_recent.assert_called_once_with(user_id=1, limit=6)
