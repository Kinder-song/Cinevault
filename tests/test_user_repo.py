"""UserRepository encapsulates users table operations."""
from unittest.mock import MagicMock

from repositories.user_repo import UserRepository


def test_get_by_id():
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": 1, "username": "admin"}
    repo = UserRepository(cursor)
    user = repo.get_by_id(1)
    assert user["username"] == "admin"


def test_get_by_username():
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": 1, "password_hash": "x"}
    repo = UserRepository(cursor)
    user = repo.get_by_username("admin")
    assert user["id"] == 1


def test_username_exists_returns_true():
    cursor = MagicMock()
    cursor.fetchone.return_value = {"id": 1}
    repo = UserRepository(cursor)
    assert repo.username_exists("admin", exclude_id=2) is True


def test_username_exists_returns_false():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    repo = UserRepository(cursor)
    assert repo.username_exists("admin", exclude_id=2) is False


def test_update_profile_applies_all_fields():
    cursor = MagicMock()
    repo = UserRepository(cursor)
    repo.update_profile(
        user_id=1,
        username="new",
        password_hash="hash",
        video_path="/videos",
        password_changed=True,
    )
    sql = cursor.execute.call_args[0][0]
    assert "username = %s" in sql
    assert "password_hash = %s" in sql
    assert "video_path = %s" in sql
    assert "password_changed = %s" in sql


def test_update_profile_username_only():
    cursor = MagicMock()
    repo = UserRepository(cursor)
    repo.update_profile(user_id=1, username="new")
    sql = cursor.execute.call_args[0][0]
    assert "username = %s" in sql
    assert "password_hash" not in sql
