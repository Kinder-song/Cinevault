"""TagRepository encapsulates tags + video_tags join table operations."""
from unittest.mock import MagicMock

from repositories.tag_repo import TagRepository


def test_get_or_create_tag_existing():
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": 5, "color": "#ff0000"}
    repo = TagRepository(cursor)
    tag_id = repo.get_or_create_tag("action")
    assert tag_id == 5
    # Only the SELECT was executed (no INSERT for an existing tag)
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "SELECT id, color FROM tags" in sql


def test_get_or_create_tag_new():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    cursor.lastrowid = 10
    repo = TagRepository(cursor)
    tag_id = repo.get_or_create_tag("newtag")
    assert tag_id == 10
    # Two execute calls: SELECT then INSERT
    assert cursor.execute.call_count == 2
    insert_sql = cursor.execute.call_args_list[1][0][0]
    assert "INSERT INTO tags" in insert_sql


def test_attach_tag():
    cursor = MagicMock()
    repo = TagRepository(cursor)
    repo.attach_tag(video_id=1, tag_id=5)
    args = cursor.execute.call_args[0]
    assert "INSERT INTO video_tags" in args[0]
    assert args[1] == (1, 5)


def test_detach_tag_by_name():
    cursor = MagicMock()
    repo = TagRepository(cursor)
    repo.detach_tag_by_name(filename="a.mp4", tag_name="action")
    args = cursor.execute.call_args[0]
    assert "DELETE" in args[0]
    assert "v.filename = %s" in args[0]
    assert args[1] == ("a.mp4", "action")


def test_list_tags_for_video():
    cursor = MagicMock()
    cursor.fetchall.return_value = [{"name": "a", "color": "#fff"}]
    repo = TagRepository(cursor)
    result = repo.list_tags_for_video("a.mp4")
    assert result[0]["name"] == "a"
    sql = cursor.execute.call_args[0][0]
    assert "SELECT t.name, t.color" in sql
