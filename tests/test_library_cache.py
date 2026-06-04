"""LibraryCache returns cached results when files are unchanged."""
import os
import tempfile
import time

from services.library_cache import LibraryCache, VIDEO_EXTENSIONS


def test_cache_returns_empty_on_first_scan():
    with tempfile.TemporaryDirectory() as d:
        cache = LibraryCache(d)
        result = cache.scan()
        assert result == {}


def test_cache_returns_files_on_second_scan_without_changes():
    with tempfile.TemporaryDirectory() as d:
        _make_video(d, "a.mp4")
        cache = LibraryCache(d)
        first = cache.scan()
        second = cache.scan()
        assert first == second
        assert "a.mp4" in first


def test_cache_detects_new_file():
    with tempfile.TemporaryDirectory() as d:
        cache = LibraryCache(d)
        cache.scan()
        _make_video(d, "b.mp4")
        result = cache.scan()
        assert "b.mp4" in result


def test_cache_detects_modified_file_by_mtime():
    with tempfile.TemporaryDirectory() as d:
        path = _make_video(d, "a.mp4")
        cache = LibraryCache(d)
        cache.scan()
        # Bump mtime into the future
        future = time.time() + 10
        os.utime(path, (future, future))
        result = cache.scan()
        assert result["a.mp4"]["mtime"] == int(future)


def test_cache_ignores_non_video_files():
    with tempfile.TemporaryDirectory() as d:
        # Non-video files should not be returned
        open(os.path.join(d, "readme.txt"), "w").close()
        cache = LibraryCache(d)
        result = cache.scan()
        assert "readme.txt" not in result


def test_cache_returns_absolute_paths():
    with tempfile.TemporaryDirectory() as d:
        _make_video(d, "a.mp4")
        cache = LibraryCache(d)
        result = cache.scan()
        assert os.path.isabs(result["a.mp4"]["path"])


def test_cache_handles_missing_directory():
    """A non-existent directory should not crash; returns empty dict."""
    cache = LibraryCache("/nonexistent/path/that/does/not/exist")
    result = cache.scan()
    assert result == {}


def test_invalidate_clears_cache():
    with tempfile.TemporaryDirectory() as d:
        _make_video(d, "a.mp4")
        cache = LibraryCache(d)
        cache.scan()
        assert cache._cache  # has entries
        cache.invalidate()
        assert not cache._cache


def _make_video(directory, name):
    """Create a file with a known video extension."""
    path = os.path.join(directory, name)
    with open(path, "wb") as f:
        f.write(b"\x00" * 1024)
    return path
