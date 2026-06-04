"""Repository for the ``share_tokens`` table."""
import datetime
from typing import Any, Dict, Optional


class ShareRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def create(self, token: str, video_filename: str, expires_at) -> int:
        self.cursor.execute(
            "INSERT INTO share_tokens (token, video_filename, expires_at) VALUES (%s, %s, %s)",
            (token, video_filename, expires_at),
        )
        return self.cursor.lastrowid

    def get_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT st.*, v.filename, v.title, v.duration, v.file_size
            FROM share_tokens st
            JOIN videos v ON v.filename = st.video_filename
            WHERE st.token = %s
            """,
            (token,),
        )
        return self.cursor.fetchone()

    def cleanup_expired(self) -> int:
        """Delete share tokens whose ``expires_at`` is in the past.

        Returns:
            Number of rows deleted.
        """
        self.cursor.execute(
            "DELETE FROM share_tokens WHERE expires_at < %s",
            (datetime.datetime.utcnow(),),
        )
        return self.cursor.rowcount
