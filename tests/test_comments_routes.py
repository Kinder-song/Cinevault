"""Verify /api/video/<f>/comments routes use CommentRepository after refactor."""
from unittest.mock import patch, MagicMock
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


@pytest.fixture
def non_admin_client():
    """Same as ``client`` but with a non-admin user so the
    `delete_owned` path is exercised (admin path uses raw SQL).
    """
    app.config["TESTING"] = True
    app.config["CSRF_DISABLE"] = True
    original = csrf._csrf_disable
    csrf._csrf_disable = True
    try:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = 2
                sess["username"] = "alice"
            yield c
    finally:
        csrf._csrf_disable = original


def test_post_comment(client):
    with patch("routes.comments.CommentRepository") as Repo, \
         patch("routes.comments.VideoRepository") as Vid:
        Vid.return_value.get_by_filename.return_value = {"id": 5}
        Repo.return_value.add.return_value = 99
        res = client.post(
            "/api/video/a.mp4/comments",
            json={"content": "Great video!"},
        )
        assert res.status_code == 200
        assert res.get_json()["id"] == 99


def test_post_empty_comment_rejected(client):
    res = client.post(
        "/api/video/a.mp4/comments",
        json={"content": ""},
    )
    assert res.status_code == 400


def test_list_comments(client):
    with patch("routes.comments.CommentRepository") as Repo, \
         patch("routes.comments.VideoRepository") as Vid:
        Vid.return_value.get_by_filename.return_value = {"id": 5}
        Repo.return_value.list_for_video.return_value = [
            {"id": 1, "content": "Hi", "username": "alice", "created_at": "2024-01-01"}
        ]
        res = client.get("/api/video/a.mp4/comments")
        data = res.get_json()
        assert len(data["comments"]) == 1


def test_delete_own_comment(non_admin_client):
    """A non-admin user deleting their own comment goes through
    ``delete_owned``. (Admin path uses raw SQL and is verified
    separately in ``test_admin_delete_uses_raw_sql``.)"""
    with patch("routes.comments.CommentRepository") as Repo:
        Repo.return_value.delete_owned.return_value = True
        res = non_admin_client.delete("/api/comments/42")
        assert res.status_code == 200
        # Route calls delete_owned positionally: (comment_id, user_id)
        Repo.return_value.delete_owned.assert_called_once_with(42, 2)


def test_delete_others_comment_forbidden(non_admin_client):
    """Users can only delete their own comments unless admin."""
    with patch("routes.comments.CommentRepository") as Repo:
        Repo.return_value.delete_owned.return_value = False
        res = non_admin_client.delete("/api/comments/42")
        assert res.status_code == 403


def test_admin_delete_uses_raw_sql(client):
    """Admin path bypasses ``delete_owned`` and issues raw SQL on the
    underlying cursor."""
    with patch("routes.comments.CommentRepository") as Repo:
        # The mocked class is instantiated with the db cursor; configure
        # rowcount on that cursor so the admin branch reports success.
        Repo.return_value.delete_owned.return_value = False
        with patch("routes.comments.with_db_cursor") as wdc:
            cursor = MagicMock()
            cursor.rowcount = 1
            wdc.return_value.__enter__.return_value = cursor
            res = client.delete("/api/comments/42")
        assert res.status_code == 200
        # delete_owned should NOT be called on the admin path
        Repo.return_value.delete_owned.assert_not_called()
