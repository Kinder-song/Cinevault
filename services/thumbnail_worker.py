"""Background thumbnail generation worker.

Admin-triggered thumbnail regeneration runs in a separate thread so the
HTTP request returns immediately with a job ID. Status is queried via
``GET /api/sync/thumbnail-status/<id>``.
"""
import os
import queue
import threading
import uuid
from typing import Dict

from services.video_service import generate_thumbnail
from utils.logger import sync_logger


class ThumbnailWorker:
    """Single-threaded thumbnail job queue with status tracking."""

    def __init__(self, thumbnail_dir: str = None):
        from config import Config
        self.thumbnail_dir = thumbnail_dir or Config.THUMBNAIL_DIR
        self._queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._status: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the worker thread (idempotent)."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5) -> None:
        """Signal the worker to stop. Joins the thread with a timeout."""
        self._stop_event.set()
        thread = self._thread
        if thread:
            thread.join(timeout=timeout)

    def enqueue(self, job_id: str, video_path: str) -> str:
        """Queue a thumbnail job. Returns the job_id."""
        with self._lock:
            self._status[job_id] = "pending"
        self._queue.put((job_id, video_path))
        return job_id

    def status(self, job_id: str) -> str:
        """Return the current status of a job.

        Returns one of: "pending", "running", "done", "failed", "unknown".
        "unknown" is returned for any job_id that was never enqueued.
        """
        with self._lock:
            return self._status.get(job_id, "unknown")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id, video_path = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            with self._lock:
                self._status[job_id] = "running"
            try:
                if not os.path.exists(video_path):
                    raise FileNotFoundError(video_path)
                safe_name = os.path.splitext(os.path.basename(video_path))[0]
                result = generate_thumbnail(safe_name, video_path)
                if not result or not os.path.exists(result):
                    raise RuntimeError("ffmpeg produced no thumbnail")
                with self._lock:
                    self._status[job_id] = "done"
            except Exception as e:
                sync_logger.error("Thumbnail job %s failed: %s", job_id, e)
                with self._lock:
                    self._status[job_id] = "failed"
            finally:
                self._queue.task_done()


# Module-level singleton + convenience functions for use in routes
_worker_instance: ThumbnailWorker | None = None


def start_worker() -> None:
    """Start the module-level worker singleton."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = ThumbnailWorker()
    _worker_instance.start()


def stop_worker() -> None:
    """Stop the module-level worker singleton (idempotent)."""
    global _worker_instance
    if _worker_instance is not None:
        _worker_instance.stop()
        _worker_instance = None


def submit_thumbnail_job(video_path: str) -> str:
    """Submit a thumbnail job and return its job_id."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = ThumbnailWorker()
        _worker_instance.start()
    return _worker_instance.enqueue(str(uuid.uuid4()), video_path)


def get_thumbnail_status(job_id: str) -> str:
    """Get the status of a previously submitted job."""
    if _worker_instance is None:
        return "unknown"
    return _worker_instance.status(job_id)
