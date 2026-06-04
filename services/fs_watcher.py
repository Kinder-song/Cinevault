"""Filesystem watcher that detects new files in a directory.

Polling-based (no external dependencies). Disabled by default — enable
via ``ENABLE_FS_WATCHER=1`` in .env. When a new file appears, the
callback is invoked with the full path; the callback is expected to
invalidate the relevant LibraryCache entry.
"""
import os
import threading

from utils.logger import sync_logger


class FSWatcher:
    """Polling-based directory watcher.

    Snapshots the directory contents at ``start()`` time; on each poll
    cycle, computes the diff and invokes the callback for new files.

    Polling interval is 5 seconds. For finer granularity or recursive
    watching, install the ``watchdog`` package and replace the polling
    loop with ``watchdog.observers.Observer``.
    """

    POLL_INTERVAL_SECONDS = 5

    def __init__(self, watch_dir: str, callback):
        self.watch_dir = os.path.abspath(watch_dir)
        self.callback = callback
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._known: set[str] = set()

    def start(self) -> None:
        """Start the polling thread. No-op if already started."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        # Snapshot existing files; only NEW files after this point trigger events.
        if os.path.isdir(self.watch_dir):
            try:
                self._known = set(os.listdir(self.watch_dir))
            except OSError as e:
                sync_logger.warning(
                    "FSWatcher could not list %s: %s", self.watch_dir, e
                )
                self._known = set()
        else:
            sync_logger.warning(
                "FSWatcher started but %s is not a directory", self.watch_dir
            )
            self._known = set()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2) -> None:
        """Stop the polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _poll(self) -> None:
        while not self._stop_event.is_set():
            try:
                if os.path.isdir(self.watch_dir):
                    current = set(os.listdir(self.watch_dir))
                    new_files = current - self._known
                    for filename in new_files:
                        full_path = os.path.join(self.watch_dir, filename)
                        try:
                            self.callback(full_path)
                        except Exception as e:
                            sync_logger.warning(
                                "FSWatcher callback error for %s: %s", full_path, e
                            )
                    self._known = current
            except Exception as e:
                sync_logger.warning("FSWatcher poll error: %s", e)
            # Sleep with early-exit on stop
            self._stop_event.wait(timeout=self.POLL_INTERVAL_SECONDS)
