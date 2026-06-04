"""In-memory cache of video library file state.

Caches the result of ``scandir`` keyed by ``(size, mtime)`` so we can
skip files that haven't changed since the last scan. This is the foundation
for incremental sync — only new/changed files get ffmpeg-probed.
"""
import os
from typing import Any, Dict


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}


class LibraryCache:
    """Caches a directory's video file metadata across scans.

    Usage:
        cache = LibraryCache("/path/to/videos")
        result = cache.scan()  # {filename: {path, size, mtime}}
        # later...
        result = cache.scan()  # only re-stats changed files

    The internal ``_cache`` is the previous scan result. A file is considered
    "changed" if its current ``(size, mtime)`` differs from the cached one.
    """

    def __init__(self, video_dir: str):
        self.video_dir = os.path.abspath(video_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def scan(self) -> Dict[str, Dict[str, Any]]:
        """Return ``{filename: {path, size, mtime}}`` for all videos.

        Reuses previous result when ``(size, mtime)`` matches.
        """
        result: Dict[str, Dict[str, Any]] = {}
        if not os.path.isdir(self.video_dir):
            self._cache = {}
            return result

        for entry in os.scandir(self.video_dir):
            if not entry.is_file():
                continue
            ext = os.path.splitext(entry.name)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            size = stat.st_size
            mtime = int(stat.st_mtime)

            cached = self._cache.get(entry.name)
            if cached and cached["size"] == size and cached["mtime"] == mtime:
                result[entry.name] = cached
            else:
                result[entry.name] = {
                    "path": entry.path,
                    "size": size,
                    "mtime": mtime,
                }

        self._cache = result
        return result

    def invalidate(self, filename: str | None = None) -> None:
        """Clear the cache, or just one file's entry.

        Args:
            filename: If given, only this file is invalidated. If None,
                the whole cache is cleared.
        """
        if filename is None:
            self._cache.clear()
        else:
            self._cache.pop(filename, None)
