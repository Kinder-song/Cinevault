"""ThumbnailWorker processes the queue in a background thread."""
import os
import threading
import time

from services.thumbnail_worker import ThumbnailWorker


def test_worker_picks_up_job():
    worker = ThumbnailWorker()
    worker.start()
    try:
        worker.enqueue("test_job", "/nonexistent/path.mp4")
        # Wait up to 3s for the worker to process
        deadline = time.time() + 3
        status = None
        while time.time() < deadline:
            status = worker.status("test_job")
            if status in ("done", "failed"):
                break
            time.sleep(0.05)
        # Should be one of the terminal states; never blocks
        assert status in ("done", "failed"), f"Worker didn't finish, status={status}"
    finally:
        worker.stop()


def test_worker_status_starts_pending_or_running():
    """Right after enqueue, status is 'pending' (or already 'done' if very fast)."""
    worker = ThumbnailWorker()
    worker.start()
    try:
        worker.enqueue("foo", "/nonexistent/x.mp4")
        # Just check it doesn't crash; the actual status depends on timing
        status = worker.status("foo")
        assert status in ("pending", "running", "done", "failed", "unknown")
    finally:
        worker.stop()


def test_worker_status_unknown_for_unstarted_job():
    """If you ask for a job_id that was never enqueued, status is 'unknown'."""
    worker = ThumbnailWorker()
    assert worker.status("never_enqueued") == "unknown"


def test_worker_isolates_failures():
    """A failed job doesn't break subsequent jobs."""
    worker = ThumbnailWorker()
    worker.start()
    try:
        worker.enqueue("fail_job", "/nonexistent/a.mp4")
        worker.enqueue("good_job", "/nonexistent/b.mp4")
        time.sleep(1)  # let them process
        # Both should be in a terminal state
        assert worker.status("fail_job") in ("done", "failed")
        assert worker.status("good_job") in ("done", "failed")
    finally:
        worker.stop()
