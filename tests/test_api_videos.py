"""Verify /api/videos respects search and sort parameters correctly."""
from unittest.mock import patch
import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["video_path"] = "/tmp"
        yield c


def test_search_filters_results(client):
    """search=keyword should only return matching videos."""
    with patch("routes.videos.sync_and_get_videos") as sync, \
         patch("routes.videos.with_db_cursor") as cursor:
        sync.return_value = [
            {"filename": "a.mp4", "title": "Action movie", "size": 100,
             "size_bytes": 100, "duration": 60, "duration_formatted": "1:00",
             "duration_raw": 60, "created_at": "2024-01-01",
             "width": 1920, "height": 1080, "fps": 30, "bitrate": 5000,
             "is_favorite": False, "rating": 0, "progress": 0,
             "watched_duration": 0, "thumbnail": None, "filesize": "100 B"},
            {"filename": "b.mp4", "title": "Comedy show", "size": 200,
             "size_bytes": 200, "duration": 30, "duration_formatted": "0:30",
             "duration_raw": 30, "created_at": "2024-01-02",
             "width": 1280, "height": 720, "fps": 24, "bitrate": 3000,
             "is_favorite": False, "rating": 0, "progress": 0,
             "watched_duration": 0, "thumbnail": None, "filesize": "200 B"},
        ]
        cursor.return_value.__enter__.return_value.fetchall.return_value = []
        res = client.get("/api/videos?search=action")
        data = res.get_json()
        assert len(data["videos"]) == 1
        assert data["videos"][0]["filename"] == "a.mp4"
        assert data["total"] == 1


def test_sort_by_size_descending(client):
    """sort=size_bytes&order=desc returns largest first."""
    with patch("routes.videos.sync_and_get_videos") as sync, \
         patch("routes.videos.with_db_cursor") as cursor:
        sync.return_value = [
            {"filename": "a.mp4", "title": "A", "size": 100, "size_bytes": 100,
             "file_size": 100,
             "duration": 60, "duration_formatted": "1:00", "duration_raw": 60,
             "created_at": "2024-01-01",
             "width": 0, "height": 0, "fps": None, "bitrate": None,
             "is_favorite": False, "rating": 0, "progress": 0,
             "watched_duration": 0, "thumbnail": None, "filesize": "100 B"},
            {"filename": "b.mp4", "title": "B", "size": 200, "size_bytes": 200,
             "file_size": 200,
             "duration": 30, "duration_formatted": "0:30", "duration_raw": 30,
             "created_at": "2024-01-02",
             "width": 0, "height": 0, "fps": None, "bitrate": None,
             "is_favorite": False, "rating": 0, "progress": 0,
             "watched_duration": 0, "thumbnail": None, "filesize": "200 B"},
        ]
        cursor.return_value.__enter__.return_value.fetchall.return_value = []
        res = client.get("/api/videos?sort=size_bytes&order=desc")
        data = res.get_json()
        assert data["videos"][0]["filename"] == "b.mp4"


def test_page_beyond_filtered_total_returns_empty_with_correct_total(client):
    """When a search filter narrows results, page numbers must reflect the
    filtered count, not the pre-filter count."""
    with patch("routes.videos.sync_and_get_videos") as sync, \
         patch("routes.videos.with_db_cursor") as cursor:
        sync.return_value = [
            {"filename": "a.mp4", "title": "Match this", "size": 100,
             "size_bytes": 100, "file_size": 100,
             "duration": 60, "duration_formatted": "1:00",
             "duration_raw": 60, "created_at": "2024-01-01",
             "width": 0, "height": 0, "fps": None, "bitrate": None,
             "is_favorite": False, "rating": 0, "progress": 0,
             "watched_duration": 0, "thumbnail": None, "filesize": "100 B"},
            {"filename": "b.mp4", "title": "Other content", "size": 200,
             "size_bytes": 200, "file_size": 200,
             "duration": 30, "duration_formatted": "0:30",
             "duration_raw": 30, "created_at": "2024-01-02",
             "width": 0, "height": 0, "fps": None, "bitrate": None,
             "is_favorite": False, "rating": 0, "progress": 0,
             "watched_duration": 0, "thumbnail": None, "filesize": "200 B"},
        ]
        cursor.return_value.__enter__.return_value.fetchall.return_value = []
        res = client.get("/api/videos?search=match&page=10&per_page=24")
        data = res.get_json()
        # After filter, only 1 result, page 10 is out of range
        assert data["videos"] == []
        assert data["total"] == 1
        assert data["total_pages"] == 1


def test_invalid_sort_falls_back_to_filename(client):
    """Unknown sort key must not 500; falls back to 'filename'."""
    with patch("routes.videos.sync_and_get_videos") as sync, \
         patch("routes.videos.with_db_cursor") as cursor:
        sync.return_value = []
        cursor.return_value.__enter__.return_value.fetchall.return_value = []
        res = client.get("/api/videos?sort=evil_injection")
        assert res.status_code == 200
        data = res.get_json()
        assert data["sort"] == "filename"
