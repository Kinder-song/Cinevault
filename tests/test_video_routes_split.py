"""Verify the videos blueprint split into 3 still serves the same routes.

After splitting ``routes/videos.py`` into ``routes/index.py``,
``routes/player.py`` and ``routes/api_videos.py``, every public URL
must remain reachable via Flask's url_map.
"""
from app import app


def test_index_route_exists():
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/" in rules


def test_video_page_route():
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/video/<path:filename>" in rules


def test_api_videos_route():
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/videos" in rules


def test_stream_route():
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/stream/<path:filename>" in rules
