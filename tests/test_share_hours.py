"""Verify share token hours are clamped and that the timezone-aware API is used."""
import datetime
import re
from unittest.mock import patch
import pytest

from app import app, csrf


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # Disable CSRF for this test (mirror the pattern in test_input_validation.py).
    # flask-seasurf 2.0 reads CSRF_DISABLE only at init_app() time, so
    # we also flip the instance flag so it takes effect in this test.
    app.config["CSRF_DISABLE"] = True
    original = csrf._csrf_disable
    csrf._csrf_disable = True
    try:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["video_path"] = "/tmp"
            yield c
    finally:
        csrf._csrf_disable = original


class TestShareHoursValidation:
    def test_negative_hours_rejected(self, client):
        with patch("services.sync_service.sync_video_to_db") as sync:
            sync.return_value = {"filename": "x.mp4"}
            res = client.post(
                "/api/video/somefile.mp4/share",
                json={"hours": -1},
            )
        assert res.status_code == 400
        body = res.get_json()
        assert "between" in body["error"].lower() or "1 and 168" in body["error"]

    def test_huge_hours_rejected(self, client):
        with patch("services.sync_service.sync_video_to_db") as sync:
            sync.return_value = {"filename": "x.mp4"}
            res = client.post(
                "/api/video/somefile.mp4/share",
                json={"hours": 999999999},
            )
        assert res.status_code == 400

    def test_zero_hours_rejected(self, client):
        with patch("services.sync_service.sync_video_to_db") as sync:
            sync.return_value = {"filename": "x.mp4"}
            res = client.post(
                "/api/video/somefile.mp4/share",
                json={"hours": 0},
            )
        assert res.status_code == 400

    def test_string_hours_rejected(self, client):
        with patch("services.sync_service.sync_video_to_db") as sync:
            sync.return_value = {"filename": "x.mp4"}
            res = client.post(
                "/api/video/somefile.mp4/share",
                json={"hours": "abc"},
            )
        assert res.status_code == 400

    def test_hours_at_lower_bound_accepted(self, client):
        """hours=1 must be accepted (or fail at the file-existence step, but
        not at the hours-validation step)."""
        with patch("services.sync_service.sync_video_to_db") as sync:
            sync.return_value = {"filename": "x.mp4"}
            res = client.post(
                "/api/video/somefile.mp4/share",
                json={"hours": 1},
            )
            # Should not be 400 from hours validation; could be 200 (success) or
            # 500 (DB mock failure); just NOT 400-from-hours.
            assert res.status_code != 400 or "between" not in res.get_data(as_text=True).lower()

    def test_hours_at_upper_bound_accepted(self, client):
        """hours=168 (7 days) is the maximum allowed."""
        with patch("services.sync_service.sync_video_to_db") as sync:
            sync.return_value = {"filename": "x.mp4"}
            res = client.post(
                "/api/video/somefile.mp4/share",
                json={"hours": 168},
            )
            assert res.status_code != 400 or "between" not in res.get_data(as_text=True).lower()


class TestTimezoneAwareDatetime:
    def test_utcnow_not_used_in_share_module(self):
        """The deprecated datetime.utcnow() must not appear in routes/share.py."""
        from pathlib import Path
        text = Path("routes/share.py").read_text()
        assert "datetime.utcnow()" not in text, (
            "datetime.utcnow() is deprecated in Python 3.12+; use "
            "datetime.now(datetime.timezone.utc)"
        )

    def test_utcnow_not_used_app_wide(self):
        """Quick scan: utcnow() should not appear anywhere in the routes/ or utils/ dirs."""
        from pathlib import Path
        bad = []
        for p in list(Path("routes").rglob("*.py")) + list(Path("utils").rglob("*.py")):
            if "datetime.utcnow()" in p.read_text():
                bad.append(str(p))
        assert not bad, f"Found deprecated utcnow() in: {bad}"
