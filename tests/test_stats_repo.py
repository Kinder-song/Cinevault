"""StatsRepository encapsulates dashboard aggregations."""
from unittest.mock import MagicMock

from repositories.stats_repo import StatsRepository


def test_get_main_stats_returns_aggregates():
    cursor = MagicMock()
    cursor.fetchone.return_value = {
        "total_videos": 10,
        "total_duration": 3600.0,
        "total_size": 1024,
        "watched_duration": 1800.0,
        "favorites": 3,
    }
    repo = StatsRepository(cursor)
    result = repo.get_main_stats()
    assert result["total_videos"] == 10
    assert result["favorites"] == 3
    sql = cursor.execute.call_args[0][0]
    assert "FROM videos" in sql
    assert "SUM(duration)" in sql
    assert "SUM(CASE WHEN favorite = 1" in sql


def test_get_tag_stats_groups_and_orders():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"name": "action", "color": "#f00", "count": 5},
        {"name": "comedy", "color": "#0f0", "count": 2},
    ]
    repo = StatsRepository(cursor)
    result = repo.get_tag_stats(limit=20)
    assert result[0]["name"] == "action"
    assert result[0]["count"] == 5
    sql = cursor.execute.call_args[0][0]
    assert "FROM tags t" in sql
    assert "LEFT JOIN video_tags vt" in sql
    assert "LIMIT %s" in sql
    assert cursor.execute.call_args[0][1] == (20,)


def test_get_tag_stats_default_limit_is_20():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    repo = StatsRepository(cursor)
    repo.get_tag_stats()
    assert cursor.execute.call_args[0][1] == (20,)


def test_get_codec_stats_groups_nonempty():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"codec": "h264", "count": 7},
        {"codec": "hevc", "count": 3},
    ]
    repo = StatsRepository(cursor)
    result = repo.get_codec_stats()
    assert result[0]["codec"] == "h264"
    sql = cursor.execute.call_args[0][0]
    assert "FROM videos" in sql
    assert "WHERE codec IS NOT NULL AND codec != ''" in sql
    assert "GROUP BY codec" in sql


def test_get_resolution_stats_buckets_by_width():
    cursor = MagicMock()
    cursor.fetchone.return_value = {"uhd": 1, "fhd": 4, "hd": 3, "sd": 2}
    repo = StatsRepository(cursor)
    result = repo.get_resolution_stats()
    assert result == {"uhd": 1, "fhd": 4, "hd": 3, "sd": 2}
    sql = cursor.execute.call_args[0][0]
    assert "width >= 3840" in sql
    assert "width >= 1920 AND width < 3840" in sql
    assert "width >= 1280 AND width < 1920" in sql
    assert "width < 1280" in sql
