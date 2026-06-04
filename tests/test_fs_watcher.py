"""FSWatcher detects new files in the watched directory."""
import os
import tempfile
import time

from services.fs_watcher import FSWatcher


def test_watcher_emits_event_for_new_file():
    with tempfile.TemporaryDirectory() as d:
        events = []
        watcher = FSWatcher(d, callback=lambda p: events.append(p))
        watcher.start()
        try:
            time.sleep(0.3)  # let watcher initialize (snapshot existing)
            new_path = os.path.join(d, "new.mp4")
            with open(new_path, "wb") as f:
                f.write(b"\x00" * 1024)
            # Wait for the polling interval (5s in production, but we
            # can poll faster in the test by patching)
            deadline = time.time() + 8
            while time.time() < deadline:
                if any("new.mp4" in e for e in events):
                    break
                time.sleep(0.2)
            assert any("new.mp4" in e for e in events), (
                f"No event for new file; events: {events}"
            )
        finally:
            watcher.stop()


def test_watcher_does_not_emit_for_initial_files():
    """Files present at start() should not trigger callback events."""
    with tempfile.TemporaryDirectory() as d:
        existing = os.path.join(d, "already_here.mp4")
        with open(existing, "wb") as f:
            f.write(b"\x00" * 1024)

        events = []
        watcher = FSWatcher(d, callback=lambda p: events.append(p))
        watcher.start()
        try:
            time.sleep(1)  # let it poll a few times
            assert not any("already_here.mp4" in e for e in events), (
                f"Initial file triggered events: {events}"
            )
        finally:
            watcher.stop()


def test_watcher_handles_nonexistent_directory_gracefully():
    """A non-existent directory should not crash; start() should be a no-op."""
    events = []
    watcher = FSWatcher("/nonexistent/path/abc/123", callback=lambda p: events.append(p))
    # Should not raise
    watcher.start()
    watcher.stop()
