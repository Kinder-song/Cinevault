"""Verify /share/<token> renders with a working video stream URL."""
import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_shared_page_renders_stream_url(client):
    """The shared.html template must reference video.filename (the dict key
    passed by the share route), not the undefined video_filename."""
    fake_video = {
        "filename": "test.mp4",
        "filesize": "1.0 MB",
        "size_bytes": 1024,
        "duration": "1:00",
        "duration_formatted": "1:00",
        "duration_raw": 60,
        "width": 1920,
        "height": 1080,
        "resolution": "1920x1080",
        "codec": "h264",
        "bitrate": "5000 kbps",
        "bitrate_raw": 5000,
        "fps": "30.00",
        "fps_raw": 30.0,
        "thumbnail": None,
        "favorite": False,
        "is_favorite": False,
        "rating": 0,
        "progress": 0,
        "watched_duration": "0:00",
        "last_watched": None,
        "created_at": None,
        "created": None,
        "size": 1024,
        "title": "Test",
        "id": 1,
        "filepath": None,
    }
    with app.app_context():
        with app.test_request_context():
            html = app.jinja_env.get_template("shared.html").render(
                video=fake_video, token="abc", title="Test"
            )
    # The stream URL must contain the encoded filename, not be empty
    assert "/stream/test.mp4" in html, (
        f"Missing /stream/<filename> URL; first 200 chars: {html[:200]!r}"
    )
