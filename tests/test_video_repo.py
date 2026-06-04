"""VideoRepository encapsulates all video table queries."""
import os
import tempfile
from unittest.mock import MagicMock

from repositories.video_repo import VideoRepository


def test_get_by_filename():
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": 1, "filename": "a.mp4", "title": "A"}
    repo = VideoRepository(cursor)
    result = repo.get_by_filename("a.mp4")
    assert result["id"] == 1
    cursor.execute.assert_called_once()
    assert "a.mp4" in cursor.execute.call_args[0][1]


def test_update_progress():
    cursor = MagicMock()
    repo = VideoRepository(cursor)
    repo.update_progress("a.mp4", 120)
    cursor.execute.assert_called_once()
    args = cursor.execute.call_args[0]
    assert "UPDATE videos SET watched_duration" in args[0]
    assert args[1] == (120, "a.mp4")


def test_toggle_favorite():
    cursor = MagicMock()
    repo = VideoRepository(cursor)
    repo.set_favorite("a.mp4", True)
    args = cursor.execute.call_args[0]
    assert args[1] == (1, "a.mp4")


def test_set_rating_clamps_to_range():
    cursor = MagicMock()
    repo = VideoRepository(cursor)
    repo.set_rating("a.mp4", 99)  # Should clamp to 5
    args = cursor.execute.call_args[0]
    assert args[1] == (5, "a.mp4")


def test_list_all():
    cursor = MagicMock()
    cursor.fetchall.return_value = [{"filename": "a.mp4"}, {"filename": "b.mp4"}]
    repo = VideoRepository(cursor)
    result = repo.list_all()
    assert len(result) == 2
