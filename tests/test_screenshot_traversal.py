"""Verify /screenshot/ cannot escape the thumbnails directory."""
import os
import tempfile
from unittest.mock import patch

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = 1
            sess["video_path"] = "/tmp/nonexistent_for_test"  # validation will fail
        yield c


class TestScreenshotTraversal:
    def test_dotdot_traversal_rejected(self, client):
        """Requesting ../app.py must not return source code."""
        res = client.get("/screenshot/../app.py")
        assert res.status_code == 404

    def test_absolute_path_rejected(self, client):
        # Werkzeug normalizes "//" → "/" with a 308 redirect; follow it to
        # verify the file is never served.
        res = client.get("/screenshot//etc/passwd", follow_redirects=True)
        assert res.status_code == 404

    def test_existing_thumbnail_served(self, client):
        """Valid thumbnails inside Config.THUMBNAIL_DIR are served."""
        with tempfile.TemporaryDirectory() as td:
            thumb_file = os.path.join(td, "test.jpg")
            with open(thumb_file, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0testjpeg")
            with patch("config.Config.THUMBNAIL_DIR", td):
                res = client.get("/screenshot/test.jpg")
                assert res.status_code == 200
                assert res.data[:3] == b"\xff\xd8\xff"

    def test_subdirectory_in_filename_rejected(self, client):
        """A filename containing path separators must be rejected (basename only)."""
        res = client.get("/screenshot/subdir/file.jpg")
        assert res.status_code == 404
