"""Verify POST endpoints reject requests without a valid CSRF token.
When CSRF is enabled and no token is supplied, SeaSurf returns 400.
"""
import os
import pytest

# Ensure CSRF is on
os.environ.setdefault("WTF_CSRF_ENABLED", "1")

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = True
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
        yield c


class TestCSRFProtection:
    def test_post_without_csrf_token_rejected(self, client):
        """POST without X-CSRF-Token header -> 403 from SeaSurf (Forbidden)."""
        res = client.post(
            "/api/video/somefile.mp4/favorite",
            json={"is_favorite": True},
        )
        # flask-seasurf 2.0 raises werkzeug.Forbidden (403) for missing token.
        # (1.x returned 400, but 2.0 is the Flask 3-compatible release.)
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        body = res.get_data(as_text=True)
        assert "CSRF" in body.upper() or "csrf" in body.lower(), (
            f"Response didn't mention CSRF: {body!r}"
        )
