"""End-to-end test of repositories against a real MySQL connection.

Skipped by default. Run with:

    INTEGRATION_DB=1 pytest tests/integration/

Requires a reachable MySQL configured via the standard env vars
(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME). If MySQL is
unreachable when INTEGRATION_DB=1 is set, the test is skipped so
that local dev environments without a DB can still run the suite.
"""
import os
import socket
import time

import pytest

from config import Config
from repositories.tag_repo import TagRepository
from repositories.video_repo import VideoRepository
from services.db_service import with_db_cursor


def _can_reach_mysql() -> bool:
    """Quick TCP probe — used to skip gracefully when no DB is up.

    A 1-second timeout is intentional: we only want a cheap "is the
    server even listening?" check, not a real connection attempt.
    The actual MySQL handshake happens in ``with_db_cursor`` once we
    decide to run the test.
    """
    host = getattr(Config, "DB_HOST", None)
    port = int(getattr(Config, "DB_PORT", None) or 3306)
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except (OSError, socket.timeout):
        return False


@pytest.mark.skipif(
    not os.getenv("INTEGRATION_DB"),
    reason="Set INTEGRATION_DB=1 to run real DB tests",
)
@pytest.mark.skipif(
    not _can_reach_mysql(),
    reason="MySQL is not reachable; skipping integration test",
)
class TestReposEndToEnd:
    def test_video_lifecycle(self):
        # Unique filename and tag name per run, so reruns don't collide
        # and cleanup is unambiguous even if a prior run left data behind.
        run_id = int(time.time() * 1000)
        filename = f"test_repo_lifecycle_{run_id}.mp4"
        tag_name = f"pytest_{run_id}"

        vid = None

        try:
            with with_db_cursor() as cursor:
                videos = VideoRepository(cursor)
                tags = TagRepository(cursor)

                vid = videos.insert(
                    filename=filename,
                    title="Integration Test",
                    file_size=0,
                    file_mtime=0,
                    duration=0,
                    width=0,
                    height=0,
                    codec="",
                    bitrate=0,
                    fps=0,
                )
                assert vid > 0, "insert() should return a positive id"

                tid = tags.get_or_create_tag(tag_name)
                assert tid > 0, "get_or_create_tag() should return a positive id"

                tags.attach_tag(vid, tid)

                listed = tags.list_tags_for_video(filename)
                assert any(
                    t["name"] == tag_name for t in listed
                ), f"tag {tag_name!r} should be attached to {filename!r}"
        finally:
            # Best-effort cleanup on a fresh connection so we don't depend
            # on the test connection still being usable. The FK on
            # video_tags.video_id has ON DELETE CASCADE, so deleting the
            # videos row removes the join row too.
            if vid is not None:
                try:
                    with with_db_cursor() as cleanup_cursor:
                        cleanup_cursor.execute(
                            "DELETE FROM videos WHERE id = %s", (vid,)
                        )
                except Exception:
                    pass
            # The tag is shared infrastructure — only delete it if this
            # test created it. The unique run_id name makes that safe.
            try:
                with with_db_cursor() as cleanup_cursor:
                    cleanup_cursor.execute(
                        "DELETE FROM tags WHERE name = %s", (tag_name,)
                    )
            except Exception:
                pass
