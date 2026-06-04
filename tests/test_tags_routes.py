"""Verify /api/video/<f>/tags routes still work after refactor."""
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


def test_add_tag_calls_repository(client):
    with patch("routes.tags.TagRepository") as TagRepo, \
         patch("routes.tags.VideoRepository") as VideoRepo:
        video_repo = VideoRepo.return_value
        tag_repo = TagRepo.return_value
        video_repo.get_by_filename.return_value = {"id": 5}
        tag_repo.get_or_create_tag.return_value = 10
        res = client.post(
            "/api/video/a.mp4/tags",
            json={"tag": "action"},
        )
        assert res.status_code == 200
        tag_repo.attach_tag.assert_called_once_with(video_id=5, tag_id=10)
