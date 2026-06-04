"""Repository for the ``users`` table."""
from typing import Any, Dict, Optional


class UserRepository:
    SAFE_UPDATE_FIELDS = {"username", "password_hash", "video_path", "password_changed"}

    def __init__(self, cursor):
        self.cursor = cursor

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, username, video_path, password_hash, password_changed "
            "FROM users WHERE id = %s",
            (user_id,),
        )
        return self.cursor.fetchone()

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, username, password_hash, password_changed "
            "FROM users WHERE username = %s",
            (username,),
        )
        return self.cursor.fetchone()

    def username_exists(self, username: str, exclude_id: int | None = None) -> bool:
        if exclude_id is not None:
            self.cursor.execute(
                "SELECT id FROM users WHERE username = %s AND id != %s",
                (username, exclude_id),
            )
        else:
            self.cursor.execute(
                "SELECT id FROM users WHERE username = %s", (username,)
            )
        return self.cursor.fetchone() is not None

    def update_profile(
        self,
        user_id: int,
        username: str | None = None,
        password_hash: str | None = None,
        video_path: str | None = None,
        password_changed: bool | None = None,
    ) -> None:
        sets = []
        params: list = []
        if username is not None:
            sets.append("username = %s")
            params.append(username)
        if password_hash is not None:
            sets.append("password_hash = %s")
            params.append(password_hash)
        if video_path is not None:
            sets.append("video_path = %s")
            params.append(video_path)
        if password_changed is not None:
            sets.append("password_changed = %s")
            params.append(password_changed)
        if not sets:
            return
        params.append(user_id)
        self.cursor.execute(
            f"UPDATE users SET {', '.join(sets)} WHERE id = %s",
            params,
        )

    def insert_default_admin(self, username: str, password_hash: str) -> None:
        self.cursor.execute(
            """
            INSERT IGNORE INTO users (username, password_hash, password_changed)
            VALUES (%s, %s, FALSE)
            """,
            (username, password_hash),
        )
