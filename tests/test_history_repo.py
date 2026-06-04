"""HistoryRepository encapsulates watch history persistence."""
from unittest.mock import MagicMock

from repositories.history_repo import HistoryRepository


def test_record_watch():
    cursor = MagicMock()
    repo = HistoryRepository(cursor)
    repo.record(user_id=1, video_id=5, watched_seconds=120)
    args = cursor.execute.call_args[0]
    assert "INSERT INTO watch_history" in args[0]


def test_list_recent():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"video_id": 5, "watched_at": "2024-01-01", "filename": "a.mp4",
         "title": "A", "thumbnail_path": "thumbnails/a.jpg"},
    ]
    repo = HistoryRepository(cursor)
    result = repo.list_recent(user_id=1, limit=20)
    assert result[0]["filename"] == "a.mp4"
    args = cursor.execute.call_args[0]
    assert "ORDER BY h.watched_at DESC" in args[0]


def test_clear_all():
    cursor = MagicMock()
    cursor.rowcount = 5
    repo = HistoryRepository(cursor)
    n = repo.clear_all(user_id=1)
    assert n == 5
