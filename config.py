import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # SECURITY: Require SECRET_KEY in production
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")

    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'video')

    # Default video root (the ./video/ folder shipped with the project)
    _default_video_root = os.path.abspath(
        os.getenv('VIDEO_PATH', './video')
    )

    # SECURITY: video_path is restricted to these roots. Users cannot set an
    # arbitrary path in their profile — they can only pick from this list.
    # Configure via env var VIDEO_ROOTS as comma-separated absolute paths,
    # or extend in code (e.g. for mounted external drives).
    _extra_roots = os.getenv('VIDEO_ROOTS', '').strip()
    VIDEO_ROOTS = [_default_video_root]
    if _extra_roots:
        VIDEO_ROOTS.extend(
            os.path.abspath(p.strip())
            for p in _extra_roots.split(',')
            if p.strip()
        )

    # Backward-compat alias for callers that still read Config.VIDEO_PATH
    # directly (fix_thumbnails.py, routes/share.py, routes/videos.py).
    VIDEO_PATH = _default_video_root

    FFMPEG_PATH = os.getenv('FFMPEG_PATH', './ffmpeg')
    # Single source of truth for the thumbnail directory. Must match what the
    # /thumbnail/<f> route serves from. Default keeps historical behavior.
    THUMBNAIL_DIR = os.getenv('THUMBNAIL_DIR', 'thumbnails')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './sessions'