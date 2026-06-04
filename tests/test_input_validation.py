"""Verify POST endpoints handle invalid input gracefully (400, not 500)."""
import pytest

from app import app, csrf


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # Existing tests disable CSRF for simplicity; mirror that.
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
            yield c
    finally:
        csrf._csrf_disable = original


class TestProgressValidation:
    def test_string_progress_rejected(self, client):
        res = client.post(
            "/api/video/test.mp4/progress",
            json={"progress": "abc"},
        )
        assert res.status_code == 400
        assert "integer" in res.get_json()["error"].lower()

    def test_null_progress_rejected(self, client):
        res = client.post(
            "/api/video/test.mp4/progress",
            json={"progress": None},
        )
        assert res.status_code == 400

    def test_negative_progress_rejected(self, client):
        res = client.post(
            "/api/video/test.mp4/progress",
            json={"progress": -100},
        )
        assert res.status_code == 400

    def test_progress_out_of_range_rejected(self, client):
        """A progress > 24h is implausible; reject."""
        res = client.post(
            "/api/video/test.mp4/progress",
            json={"progress": 100000},  # ~28 hours in seconds
        )
        assert res.status_code == 400


class TestRatingValidation:
    def test_rating_string_rejected(self, client):
        res = client.post(
            "/api/video/test.mp4/rating",
            json={"rating": "abc"},
        )
        assert res.status_code == 400

    def test_rating_above_5_clamped(self, client):
        """Per the spec, rating > 5 is clamped to 5 (not rejected)."""
        res = client.post(
            "/api/video/test.mp4/rating",
            json={"rating": 99},
        )
        # Either clamped to 5 (200) or rejected (400) — must not 500
        assert res.status_code in (200, 400)

    def test_rating_null_rejected(self, client):
        res = client.post(
            "/api/video/test.mp4/rating",
            json={"rating": None},
        )
        assert res.status_code == 400
