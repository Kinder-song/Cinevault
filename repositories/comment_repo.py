"""Repository for the ``comments`` table."""
from typing import Any, Dict, List, Optional


class CommentRepository:
    MAX_CONTENT_LENGTH = 2000

    def __init__(self, cursor):
        self.cursor = cursor

    def add(self, video_id: int, user_id: int, content: str) -> int:
        content = content.strip()[: self.MAX_CONTENT_LENGTH]
        self.cursor.execute(
            "INSERT INTO comments (video_id, user_id, content) VALUES (%s, %s, %s)",
            (video_id, user_id, content),
        )
        return self.cursor.lastrowid

    def list_for_video(self, video_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT c.id, c.content, c.created_at, c.user_id, u.username
            FROM comments c
            JOIN users u ON u.id = c.user_id
            WHERE c.video_id = %s
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (video_id, limit, offset),
        )
        return self.cursor.fetchall()

    def count_for_video(self, video_id: int) -> int:
        self.cursor.execute(
            "SELECT COUNT(*) AS c FROM comments WHERE video_id = %s",
            (video_id,),
        )
        row = self.cursor.fetchone()
        return int(row["c"]) if row else 0

    def delete_owned(self, comment_id: int, user_id: int) -> bool:
        self.cursor.execute(
            "DELETE FROM comments WHERE id = %s AND user_id = %s",
            (comment_id, user_id),
        )
        return self.cursor.rowcount > 0
