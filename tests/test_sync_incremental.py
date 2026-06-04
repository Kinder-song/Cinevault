"""sync_and_get_videos only ffmpeg-probes files whose (size, mtime) changed."""
import os
import tempfile
from unittest.mock import patch

import pytest

from services.sync_service import sync_and_get_videos


def test_sync_skips_unchanged_files(tmp_path):
    """A second call with no file changes must not invoke ffmpeg metadata probe."""
    (tmp_path / "a.mp4").write_bytes(b"\x00" * 1024)

    with patch("services.sync_service.extract_metadata") as meta, \
         patch("services.sync_service.generate_thumbnail") as thumb, \
         patch("services.sync_service.get_all_videos_from_db") as db:
        meta.return_value = {
            "duration": 10, "width": 1920, "height": 1080,
            "codec": "h264", "bitrate": 1000, "fps": 30.0,
        }
        thumb.return_value = "thumbnails/a.jpg"
        db.return_value = [
            {
                "id": 1, "filename": "a.mp4", "title": "a",
                "file_size": 1024, "file_mtime": 0,
                "duration": 10, "width": 1920, "height": 1080,
                "codec": "h264", "bitrate": 1000, "fps": 30.0,
                "favorite": 0, "rating": 0, "watched_duration": 0,
                "thumbnail_path": None, "created_at": None,
            }
        ]

        # First sync: should call extract_metadata
        sync_and_get_videos(str(tmp_path))
        first_count = meta.call_count
        assert first_count >= 1, f"Expected first sync to probe, got {first_count}"

        # Second sync: nothing changed, should NOT call again
        meta.reset_mock()
        sync_and_get_videos(str(tmp_path))
        second_count = meta.call_count
        assert second_count == 0, f"Second sync should skip, called {second_count} times"


def test_sync_probes_modified_files(tmp_path):
    """A modified file (new mtime) must trigger a re-probe."""
    path = tmp_path / "a.mp4"
    path.write_bytes(b"\x00" * 1024)

    with patch("services.sync_service.extract_metadata") as meta, \
         patch("services.sync_service.generate_thumbnail") as thumb, \
         patch("services.sync_service.get_all_videos_from_db") as db:
        meta.return_value = {
            "duration": 10, "width": 1920, "height": 1080,
            "codec": "h264", "bitrate": 1000, "fps": 30.0,
        }
        thumb.return_value = "thumbnails/a.jpg"
        db.return_value = [
            {
                "id": 1, "filename": "a.mp4", "title": "a",
                "file_size": 1024, "file_mtime": 0,
                "duration": 10, "width": 1920, "height": 1080,
                "codec": "h264", "bitrate": 1000, "fps": 30.0,
                "favorite": 0, "rating": 0, "watched_duration": 0,
                "thumbnail_path": None, "created_at": None,
            }
        ]

        sync_and_get_videos(str(tmp_path))
        first_count = meta.call_count

        # Modify the file (changes size and mtime)
        path.write_bytes(b"\x00" * 2048)
        # Bump mtime to be safe
        import time
        future = time.time() + 5
        os.utime(path, (future, future))

        meta.reset_mock()
        sync_and_get_videos(str(tmp_path))
        second_count = meta.call_count
        assert second_count >= 1, f"Modified file should trigger re-probe, got {second_count}"
