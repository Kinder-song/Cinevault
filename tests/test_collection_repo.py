"""CollectionRepository encapsulates collections + collection_videos table operations."""
from unittest.mock import MagicMock

from repositories.collection_repo import CollectionRepository


def test_list_all_returns_collections_with_count():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"id": 1, "name": "Action", "video_count": 3},
        {"id": 2, "name": "Comedy", "video_count": 0},
    ]
    repo = CollectionRepository(cursor)
    result = repo.list_all()
    assert len(result) == 2
    sql = cursor.execute.call_args[0][0]
    assert "FROM collections c" in sql
    assert "COUNT(cv.video_id)" in sql


def test_create_returns_new_id():
    cursor = MagicMock()
    cursor.lastrowid = 42
    repo = CollectionRepository(cursor)
    new_id = repo.create(name="Action", description="Action films")
    assert new_id == 42
    args = cursor.execute.call_args[0]
    assert "INSERT INTO collections" in args[0]
    assert args[1] == ("Action", "Action films")


def test_delete_cascades_member_rows():
    cursor = MagicMock()
    repo = CollectionRepository(cursor)
    repo.delete(collection_id=7)
    # Two execute calls: delete from collection_videos, then delete from collections
    assert cursor.execute.call_count == 2
    first_sql = cursor.execute.call_args_list[0][0][0]
    second_sql = cursor.execute.call_args_list[1][0][0]
    assert "DELETE FROM collection_videos" in first_sql
    assert "DELETE FROM collections" in second_sql
    assert cursor.execute.call_args_list[0][0][1] == (7,)
    assert cursor.execute.call_args_list[1][0][1] == (7,)


def test_add_video_inserts_join_row():
    cursor = MagicMock()
    repo = CollectionRepository(cursor)
    repo.add_video(collection_id=3, video_id=99)
    args = cursor.execute.call_args[0]
    assert "INSERT INTO collection_videos" in args[0]
    assert args[1] == (3, 99)


def test_get_with_videos_returns_both_collection_and_video_list():
    cursor = MagicMock()
    # First call: collection row. Second call: list of videos in collection.
    cursor.fetchone.return_value = {"id": 1, "name": "Action", "description": "x"}
    cursor.fetchall.return_value = [
        {"id": 11, "filename": "a.mp4", "title": "A"},
        {"id": 12, "filename": "b.mp4", "title": "B"},
    ]
    repo = CollectionRepository(cursor)
    result = repo.get_with_videos(collection_id=1)
    assert result["collection"]["name"] == "Action"
    assert len(result["videos"]) == 2
    # First SQL fetches the collection row, second fetches its videos
    first_sql = cursor.execute.call_args_list[0][0][0]
    second_sql = cursor.execute.call_args_list[1][0][0]
    assert "SELECT * FROM collections" in first_sql
    assert "JOIN collection_videos cv" in second_sql
    assert "ORDER BY cv.position" in second_sql
