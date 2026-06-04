"""ShareRepository encapsulates share_tokens table operations."""
from unittest.mock import MagicMock

from repositories.share_repo import ShareRepository


def test_create_inserts_token():
    cursor = MagicMock()
    cursor.lastrowid = 99
    repo = ShareRepository(cursor)
    new_id = repo.create(
        token="abc123", video_filename="movie.mp4", expires_at="2030-01-01 00:00:00"
    )
    assert new_id == 99
    args = cursor.execute.call_args[0]
    assert "INSERT INTO share_tokens" in args[0]
    assert args[1] == ("abc123", "movie.mp4", "2030-01-01 00:00:00")


def test_get_by_token_returns_joined_row():
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "token": "abc123",
        "filename": "movie.mp4",
        "title": "Movie",
        "duration": 120.0,
        "expires_at": None,
    }
    repo = ShareRepository(cursor)
    result = repo.get_by_token("abc123")
    assert result["filename"] == "movie.mp4"
    sql = cursor.execute.call_args[0][0]
    assert "FROM share_tokens st" in sql
    assert "JOIN videos v ON v.filename = st.video_filename" in sql
    assert "WHERE st.token = %s" in sql
    assert cursor.execute.call_args[0][1] == ("abc123",)


def test_get_by_token_returns_none_when_missing():
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    repo = ShareRepository(cursor)
    result = repo.get_by_token("missing")
    assert result is None


def test_cleanup_expired_deletes_old_tokens():
    cursor = MagicMock()
    cursor.rowcount = 5
    repo = ShareRepository(cursor)
    deleted = repo.cleanup_expired()
    assert deleted == 5
    sql = cursor.execute.call_args[0][0]
    assert "DELETE FROM share_tokens" in sql
    assert "expires_at < %s" in sql
    # Args should be a single timestamp argument
    assert len(cursor.execute.call_args[0][1]) == 1


def test_create_returns_lastrowid():
    cursor = MagicMock()
    cursor.lastrowid = 7
    repo = ShareRepository(cursor)
    new_id = repo.create(token="t", video_filename="v.mp4", expires_at="2030-01-01")
    assert new_id == 7
