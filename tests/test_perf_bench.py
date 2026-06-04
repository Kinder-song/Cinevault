"""Sanity perf test — guards against regressions in incremental sync.

Marked as 'slow'; skip in normal CI with `pytest -m 'not slow'`.
Run explicitly with `pytest -m slow tests/test_perf_bench.py`.
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from services.sync_service import _cache_registry, sync_and_get_videos


@pytest.fixture
def thousand_files(tmp_path):
    """Create 1000 fake video files in a temp dir."""
    for i in range(1000):
        (tmp_path / f"v{i:04d}.mp4").write_bytes(b"\x00" * 1024)
    # Ensure each run starts with a fresh LibraryCache
    _cache_registry.clear()
    return str(tmp_path)


def _fake_cursor_returning(filenames):
    """Build a context-manager mock yielding a cursor whose fetchall returns
    one dict per filename (matching the shape sync_service expects)."""
    rows = [{"filename": f} for f in filenames]
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    ctx = MagicMock()
    ctx.__enter__.return_value = cursor
    ctx.__exit__.return_value = False
    return ctx


@pytest.mark.slow
def test_thousand_files_scan_under_2s(thousand_files):
    """Scanning 1000 unchanged files should be < 2s (no ffmpeg, no DB)."""
    fake_names = [f"v{i:04d}.mp4" for i in range(1000)]

    # Patch the slow boundary so we only measure the SCAN path:
    #   - with_db_cursor: avoid real MySQL; pretend all 1000 files are in DB
    #     so the "unchanged + already-in-db" short-circuit fires
    #   - sync_video_to_db: catches any file that doesn't hit the cache
    #     (should be zero on the second call)
    #   - get_all_videos_from_db: avoid the final SELECT * to keep it pure
    with patch("services.sync_service.with_db_cursor",
               side_effect=lambda *a, **kw: _fake_cursor_returning(fake_names)), \
         patch("services.sync_service.sync_video_to_db") as sync_one, \
         patch("services.sync_service.get_all_videos_from_db") as db:
        db.return_value = []

        # Warm up: first call populates the LibraryCache
        sync_and_get_videos(thousand_files)

        # Second call: every file should hit (size, mtime) cache and be skipped
        sync_one.reset_mock()
        t0 = time.time()
        sync_and_get_videos(thousand_files)
        elapsed = time.time() - t0

        assert sync_one.call_count == 0, (
            f"Cache should short-circuit unchanged files, but "
            f"sync_video_to_db was called {sync_one.call_count} times"
        )
        assert elapsed < 2.0, f"Scan took {elapsed:.2f}s (limit 2.0s)"
