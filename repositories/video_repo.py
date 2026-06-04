"""Repository for the ``videos`` table.

Methods accept and return dicts, never the request/response objects.
The cursor is injected by the caller (typically inside a
``with_db_cursor`` context manager).
"""
from typing import Any, Dict, List, Optional


class VideoRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def get_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM videos WHERE filename = %s", (filename,)
        )
        return self.cursor.fetchone()

    def get_by_id(self, video_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT * FROM videos WHERE id = %s", (video_id,)
        )
        return self.cursor.fetchone()

    def list_all(self) -> List[Dict[str, Any]]:
        self.cursor.execute("SELECT * FROM videos ORDER BY filename")
        return self.cursor.fetchall()

    def list_filenames_with_mtime(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, filename, file_size, file_mtime FROM videos"
        )
        return self.cursor.fetchall()

    def insert(self, filename: str, title: str, file_size: int, file_mtime: int,
               duration: float, width: int, height: int, codec: str,
               bitrate: int, fps: float, thumbnail_path: str | None = None) -> int:
        self.cursor.execute(
            """
            INSERT INTO videos (
                filename, title, file_size, file_mtime, duration,
                width, height, codec, bitrate, fps, thumbnail_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (filename, title, file_size, file_mtime, duration, width, height,
             codec, bitrate, fps, thumbnail_path),
        )
        return self.cursor.lastrowid

    def update_metadata(self, filename: str, title: str, file_size: int,
                        duration: float, width: int, height: int,
                        codec: str, bitrate: int, fps: float) -> None:
        self.cursor.execute(
            """
            UPDATE videos SET
                title = %s, file_size = %s, duration = %s,
                width = %s, height = %s, codec = %s, bitrate = %s, fps = %s
            WHERE filename = %s
            """,
            (title, file_size, duration, width, height,
             codec, bitrate, fps, filename),
        )

    def update_thumbnail(self, filename: str, thumbnail_path: str) -> None:
        self.cursor.execute(
            "UPDATE videos SET thumbnail_path = %s WHERE filename = %s",
            (thumbnail_path, filename),
        )

    def update_progress(self, filename: str, progress: int) -> None:
        self.cursor.execute(
            "UPDATE videos SET watched_duration = %s WHERE filename = %s",
            (progress, filename),
        )

    def set_favorite(self, filename: str, is_favorite: bool) -> None:
        self.cursor.execute(
            "UPDATE videos SET favorite = %s WHERE filename = %s",
            (1 if is_favorite else 0, filename),
        )

    def set_rating(self, filename: str, rating: int) -> None:
        rating = max(0, min(5, int(rating)))
        self.cursor.execute(
            "UPDATE videos SET rating = %s WHERE filename = %s",
            (rating, filename),
        )
