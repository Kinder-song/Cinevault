"""Verify /api/collections routes use CollectionRepository after refactor."""
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


def test_list_collections_calls_repo_list_all(client):
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        repo.list_all.return_value = [
            {"id": 1, "name": "Action", "video_count": 3},
            {"id": 2, "name": "Comedy", "video_count": 0},
        ]
        res = client.get("/api/collections")
        assert res.status_code == 200
        data = res.get_json()
        assert "collections" in data
        assert len(data["collections"]) == 2
        repo.list_all.assert_called_once_with()


def test_create_collection_calls_repo_create(client):
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        repo.create.return_value = 42
        res = client.post(
            "/api/collections",
            json={"name": "Action", "description": "Action films"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data == {"success": True, "id": 42}
        repo.create.assert_called_once_with(
            name="Action", description="Action films"
        )


def test_create_collection_rejects_empty_name(client):
    """Validation runs before touching the repository."""
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        res = client.post("/api/collections", json={"name": "  "})
        assert res.status_code == 400
        repo.create.assert_not_called()


def test_delete_collection_calls_repo_delete(client):
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        res = client.delete("/api/collections/7")
        assert res.status_code == 200
        data = res.get_json()
        assert data == {"success": True}
        repo.delete.assert_called_once_with(collection_id=7)


def test_get_collection_with_videos_calls_repo(client):
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        repo.get_with_videos.return_value = {
            "collection": {"id": 1, "name": "Action", "description": "x"},
            "videos": [
                {"id": 11, "filename": "a.mp4", "title": "A",
                 "file_size": 0, "duration": 0, "width": 0, "height": 0,
                 "codec": "", "bitrate": 0, "fps": 0},
            ],
        }
        res = client.get("/api/collections/1")
        assert res.status_code == 200
        data = res.get_json()
        assert data["collection"]["name"] == "Action"
        assert len(data["videos"]) == 1
        # video_dict_from_row normalized the row; expect a formatted 'filesize'
        assert "filesize" in data["videos"][0]
        repo.get_with_videos.assert_called_once_with(collection_id=1)


def test_get_collection_returns_404_when_missing(client):
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        repo.get_with_videos.return_value = None
        res = client.get("/api/collections/999")
        assert res.status_code == 404
        data = res.get_json()
        assert "error" in data


def test_remove_video_calls_repo_remove_video(client):
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        # get_with_videos is used to confirm the collection exists.
        repo.get_with_videos.return_value = {
            "collection": {"id": 1, "name": "Action"},
            "videos": [],
        }
        res = client.delete("/api/collections/1/videos/a.mp4")
        assert res.status_code == 200
        repo.remove_video.assert_called_once_with(
            collection_id=1, filename="a.mp4"
        )


def test_remove_video_returns_404_when_collection_missing(client):
    with patch("routes.collections.CollectionRepository") as Repo:
        repo = Repo.return_value
        repo.get_with_videos.return_value = None
        res = client.delete("/api/collections/999/videos/a.mp4")
        assert res.status_code == 404
        repo.remove_video.assert_not_called()
