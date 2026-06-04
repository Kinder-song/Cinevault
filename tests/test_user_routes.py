"""Verify /api/user/profile and /settings routes use UserRepository after refactor."""
from unittest.mock import patch
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
            yield c
    finally:
        csrf._csrf_disable = original


def test_get_profile_calls_repo_get_by_id(client):
    with patch("routes.user.UserRepository") as Repo:
        repo = Repo.return_value
        repo.get_by_id.return_value = {
            "id": 1,
            "username": "admin",
            "video_path": "/videos",
            "password_hash": "x",
            "password_changed": True,
        }
        res = client.get("/api/user/profile")
        assert res.status_code == 200
        data = res.get_json()
        assert data["username"] == "admin"
        assert data["video_path"] == "/videos"
        repo.get_by_id.assert_called_once_with(1)


def test_get_profile_returns_404_when_missing(client):
    with patch("routes.user.UserRepository") as Repo:
        repo = Repo.return_value
        repo.get_by_id.return_value = None
        res = client.get("/api/user/profile")
        assert res.status_code == 404
        data = res.get_json()
        assert "error" in data
        repo.get_by_id.assert_called_once_with(1)


def test_settings_page_renders(client):
    with patch("routes.user.UserRepository") as Repo:
        repo = Repo.return_value
        repo.get_by_id.return_value = {
            "id": 1,
            "username": "admin",
            "video_path": "/videos",
        }
        res = client.get("/settings")
        assert res.status_code == 200
        repo.get_by_id.assert_called_once_with(1)


def test_update_profile_username_only(client):
    """POST with only username — username_exists check passes and
    update_profile is called with username only."""
    with patch("routes.user.UserRepository") as Repo:
        repo = Repo.return_value
        # username_exists returns False (no conflict)
        repo.username_exists.return_value = False
        res = client.post(
            "/api/user/profile",
            json={"username": "newname"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data == {"success": True}
        repo.username_exists.assert_called_once_with("newname", exclude_id=1)
        repo.update_profile.assert_called_once_with(
            user_id=1, username="newname"
        )


def test_update_profile_rejects_invalid_video_path(client):
    """POST with a bogus video_path (not inside any allowed root) returns 400
    and does not call update_profile."""
    # Force the configured roots to an empty list so any candidate fails.
    # The route imports Config indirectly (via utils.security which does
    # `from config import Config`), so patching the config module's
    # VIDEO_ROOTS attribute is enough.
    with patch("routes.user.UserRepository") as Repo, \
         patch("config.Config.VIDEO_ROOTS", new=[]):
        repo = Repo.return_value
        res = client.post(
            "/api/user/profile",
            json={"video_path": "/definitely/not/an/allowed/root"},
        )
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data
        # update_profile must not be called when validation fails
        repo.update_profile.assert_not_called()
