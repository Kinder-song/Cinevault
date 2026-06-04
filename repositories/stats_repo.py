"""Repository for dashboard aggregations.

The 4 methods correspond to the 4 separate queries that used to live inside
``services.db_service.get_dashboard_stats``. Each method takes a cursor and
returns a plain dict so the caller can compose them however it wants.
"""
from typing import Any, Dict, List


class StatsRepository:
    def __init__(self, cursor):
        self.cursor = cursor

    def get_main_stats(self) -> Dict[str, Any]:
        self.cursor.execute(
            """
            SELECT
                COUNT(*) as total_videos,
                COALESCE(SUM(duration), 0) as total_duration,
                COALESCE(SUM(file_size), 0) as total_size,
                COALESCE(SUM(watched_duration), 0) as watched_duration,
                COALESCE(SUM(CASE WHEN favorite = 1 THEN 1 ELSE 0 END), 0) as favorites
            FROM videos
            """
        )
        row = self.cursor.fetchone()
        if not row:
            return {
                "total_videos": 0,
                "total_duration": 0.0,
                "total_size": 0,
                "watched_duration": 0.0,
                "favorites": 0,
            }
        return {
            "total_videos": int(row["total_videos"]),
            "total_duration": float(row["total_duration"]),
            "total_size": int(row["total_size"]),
            "watched_duration": float(row["watched_duration"]),
            "favorites": int(row["favorites"]),
        }

    def get_tag_stats(self, limit: int = 20) -> List[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT t.name, t.color, COUNT(vt.video_id) as count
            FROM tags t
            LEFT JOIN video_tags vt ON t.id = vt.tag_id
            GROUP BY t.id, t.name, t.color
            ORDER BY count DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [
            {"name": r["name"], "color": r["color"], "count": int(r["count"])}
            for r in self.cursor.fetchall()
        ]

    def get_codec_stats(self) -> List[Dict[str, Any]]:
        self.cursor.execute(
            """
            SELECT codec, COUNT(*) as count
            FROM videos
            WHERE codec IS NOT NULL AND codec != ''
            GROUP BY codec
            ORDER BY count DESC
            """
        )
        return [
            {"codec": r["codec"], "count": int(r["count"])}
            for r in self.cursor.fetchall()
        ]

    def get_resolution_stats(self) -> Dict[str, int]:
        self.cursor.execute(
            """
            SELECT
                SUM(CASE WHEN width >= 3840 THEN 1 ELSE 0 END) as uhd,
                SUM(CASE WHEN width >= 1920 AND width < 3840 THEN 1 ELSE 0 END) as fhd,
                SUM(CASE WHEN width >= 1280 AND width < 1920 THEN 1 ELSE 0 END) as hd,
                SUM(CASE WHEN width < 1280 THEN 1 ELSE 0 END) as sd
            FROM videos
            """
        )
        res_row = self.cursor.fetchone()
        if not res_row:
            return {"uhd": 0, "fhd": 0, "hd": 0, "sd": 0}
        return {
            "uhd": int(res_row["uhd"] or 0),
            "fhd": int(res_row["fhd"] or 0),
            "hd": int(res_row["hd"] or 0),
            "sd": int(res_row["sd"] or 0),
        }
