"""Repository for the ``collections`` and ``collection_videos`` join table."""
from typing import Any, Dict, List, Optional


class CollectionRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def list_all(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT c.id, c.name, c.description, c.created_at,
                   COUNT(cv.video_id) as video_count
            FROM collections c
            LEFT JOIN collection_videos cv ON c.id = cv.collection_id
            GROUP BY c.id
            ORDER BY c.name
            """
        )
        return self.cursor.fetchall()

    def create(self, name: str, description: str = "") -> int:
        self.cursor.execute(
            "INSERT INTO collections (name, description) VALUES (%s, %s)",
            (name, description),
        )
        return self.cursor.lastrowid

    def delete(self, collection_id: int) -> None:
        self.cursor.execute(
            "DELETE FROM collection_videos WHERE collection_id = %s",
            (collection_id,),
        )
        self.cursor.execute(
            "DELETE FROM collections WHERE id = %s",
            (collection_id,),
        )

    def add_video(self, collection_id: int, video_id: int) -> None:
        try:
            self.cursor.execute(
                "INSERT INTO collection_videos (collection_id, video_id) VALUES (%s, %s)",
                (collection_id, video_id),
            )
        except Exception:
            pass  # already in collection

    def remove_video(self, collection_id: int, filename: str) -> None:
        self.cursor.execute(
            """
            DELETE cv FROM collection_videos cv
            JOIN videos v ON v.id = cv.video_id
            WHERE cv.collection_id = %s AND v.filename = %s
            """,
            (collection_id, filename),
        )

    def get_with_videos(self, collection_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM collections WHERE id = %s",
            (collection_id,),
        )
        collection = self.cursor.fetchone()
        if not collection:
            return None

        self.cursor.execute(
            """
            SELECT v.* FROM videos v
            JOIN collection_videos cv ON v.id = cv.video_id
            WHERE cv.collection_id = %s
            ORDER BY cv.position, v.filename
            """,
            (collection_id,),
        )
        videos = list(self.cursor.fetchall())
        return {"collection": collection, "videos": videos}
