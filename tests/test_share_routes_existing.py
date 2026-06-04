"""Verify /api/video/<f>/share and /share/<token> routes use ShareRepository
after the Plan 3 Task 6 refactor.

The name is intentionally distinct from tests/test_share_route.py (template
rendering) and tests/test_share_hours.py (hours validation) to avoid
filename collisions during pytest collection.
"""
from unittest.mock import patch
import datetime
import pytest

from app import app, csrf


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # flask-seasurf 2.0 reads CSRF_DISABLE only at init_app() time, so
    # also flip the instance flag so it takes effect in this test.
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


def test_create_share_token_calls_repo(client):
    """POST /api/video/<f>/share inserts a share token via ShareRepository."""
    with patch("services.sync_service.sync_video_to_db") as sync, \
         patch("routes.share.ShareRepository") as Repo:
        sync.return_value = {"filename": "x.mp4"}
        repo = Repo.return_value
        repo.create.return_value = 7
        res = client.post(
            "/api/video/x.mp4/share",
            json={"hours": 24},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "token" in data
        assert data["url"].startswith("/share/")
        # Repository's create() must have been called with the filename and
        # a datetime expiry. We don't pin the exact timestamp.
        assert repo.create.call_count == 1
        # create(token, video_filename, expires_at) — called with kwargs
        kwargs = repo.create.call_args.kwargs
        assert kwargs["video_filename"] == "x.mp4"
        assert isinstance(kwargs["expires_at"], datetime.datetime)
        assert isinstance(kwargs["token"], str)
        assert len(kwargs["token"]) > 0


def test_create_share_token_default_hours(client):
    """POST with no JSON body defaults to 24 hours and still creates a token."""
    with patch("services.sync_service.sync_video_to_db") as sync, \
         patch("routes.share.ShareRepository") as Repo:
        sync.return_value = {"filename": "y.mp4"}
        repo = Repo.return_value
        repo.create.return_value = 8
        res = client.post("/api/video/y.mp4/share")
        assert res.status_code == 200
        assert res.get_json()["success"] is True
        assert repo.create.call_count == 1


def test_shared_video_renders_for_valid_token(client):
    """GET /share/<token> renders shared.html when ShareRepository returns
    a non-expired share row."""
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    with patch("routes.share.ShareRepository") as Repo:
        repo = Repo.return_value
        repo.get_by_token.return_value = {
            "token": "abc123",
            "filename": "movie.mp4",
            "title": "Movie",
            "duration": 120.0,
            "file_size": 1024,
            "expires_at": future.replace(tzinfo=None),
        }
        res = client.get("/share/abc123")
        assert res.status_code == 200
        repo.get_by_token.assert_called_once_with("abc123")


def test_shared_video_returns_404_for_missing_token(client):
    """GET /share/<token> returns 404 when no share row exists."""
    with patch("routes.share.ShareRepository") as Repo:
        repo = Repo.return_value
        repo.get_by_token.return_value = None
        res = client.get("/share/does-not-exist")
        assert res.status_code == 404
        repo.get_by_token.assert_called_once_with("does-not-exist")


def test_shared_video_returns_410_for_expired_token(client):
    """GET /share/<token> returns 410 when the share has expired."""
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    with patch("routes.share.ShareRepository") as Repo:
        repo = Repo.return_value
        repo.get_by_token.return_value = {
            "token": "expired",
            "filename": "old.mp4",
            "title": "Old",
            "duration": 60.0,
            "file_size": 0,
            "expires_at": past.replace(tzinfo=None),
        }
        res = client.get("/share/expired")
        assert res.status_code == 410
