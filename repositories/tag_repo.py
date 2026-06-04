"""Repository for the ``tags`` and ``video_tags`` join table."""
from typing import Any, Dict, List, Optional


class TagRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, color FROM tags WHERE name = %s", (name,)
        )
        return self.cursor.fetchone()

    def get_or_create_tag(self, name: str) -> int:
        existing = self.get_by_name(name)
        if existing:
            return existing["id"]
        self.cursor.execute("INSERT INTO tags (name) VALUES (%s)", (name,))
        return self.cursor.lastrowid

    def attach_tag(self, video_id: int, tag_id: int) -> None:
        try:
            self.cursor.execute(
                "INSERT INTO video_tags (video_id, tag_id) VALUES (%s, %s)",
                (video_id, tag_id),
            )
        except Exception:
            pass  # already linked

    def detach_tag_by_name(self, filename: str, tag_name: str) -> None:
        self.cursor.execute(
            """
            DELETE vt FROM video_tags vt
            JOIN videos v ON v.id = vt.video_id
            JOIN tags t ON t.id = vt.tag_id
            WHERE v.filename = %s AND t.name = %s
            """,
            (filename, tag_name),
        )

    def list_tags_for_video(self, filename: str) -> List[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT t.name, t.color
            FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            JOIN videos v ON v.id = vt.video_id
            WHERE v.filename = %s
            """,
            (filename,),
        )
        return self.cursor.fetchall()

    def list_tags_by_video(self) -> Dict[str, List[Dict[str, Any]]]:
        self.cursor.execute(
            """
            SELECT t.name, t.color, v.filename
            FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            JOIN videos v ON v.id = vt.video_id
            """
        )
        result: Dict[str, list] = {}
        for row in self.cursor.fetchall():
            result.setdefault(row["filename"], []).append({
                "name": row["name"],
                "color": row["color"],
            })
        return result
