"""Repository for the ``watch_history`` table."""
from typing import Any, Dict, List


class HistoryRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def record(self, user_id: int, video_id: int, watched_seconds: int) -> None:
        self.cursor.execute(
            """
            INSERT INTO watch_history (user_id, video_id, watched_seconds)
            VALUES (%s, %s, %s)
            """,
            (user_id, video_id, watched_seconds),
        )

    def list_recent(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT h.watched_at, h.watched_seconds,
                   v.id AS video_id, v.filename, v.title, v.thumbnail_path
            FROM watch_history h
            JOIN videos v ON v.id = h.video_id
            WHERE h.user_id = %s
            ORDER BY h.watched_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return self.cursor.fetchall()

    def clear_all(self, user_id: int) -> int:
        self.cursor.execute(
            "DELETE FROM watch_history WHERE user_id = %s", (user_id,)
        )
        return self.cursor.rowcount
