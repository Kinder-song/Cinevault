"""CommentRepository encapsulates the comments table."""
from unittest.mock import MagicMock
from repositories.comment_repo import CommentRepository


def test_add_comment():
    cursor = MagicMock()
    cursor.lastrowid = 42
    repo = CommentRepository(cursor)
    cid = repo.add(video_id=1, user_id=2, content="Hello")
    assert cid == 42
    args = cursor.execute.call_args[0]
    assert "INSERT INTO comments" in args[0]
    assert args[1] == (1, 2, "Hello")


def test_list_for_video():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"id": 1, "content": "Hi", "username": "alice", "created_at": "2024-01-01"},
    ]
    repo = CommentRepository(cursor)
    result = repo.list_for_video(video_id=5)
    assert len(result) == 1
    assert result[0]["username"] == "alice"


def test_delete_by_id_owned():
    cursor = MagicMock()
    cursor.rowcount = 1
    repo = CommentRepository(cursor)
    deleted = repo.delete_owned(comment_id=10, user_id=2)
    assert deleted is True


def test_count_for_video():
    cursor = MagicMock()
    cursor.fetchone.return_value = {"c": 17}
    repo = CommentRepository(cursor)
    assert repo.count_for_video(5) == 17
