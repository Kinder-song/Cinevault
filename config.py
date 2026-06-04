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
    VIDEO_PATH = os.getenv('VIDEO_PATH', './video')
    FFMPEG_PATH = os.getenv('FFMPEG_PATH', './ffmpeg')
    # Single source of truth for the thumbnail directory. Must match what the
    # /thumbnail/<f> route serves from. Default keeps historical behavior.
    THUMBNAIL_DIR = os.getenv('THUMBNAIL_DIR', 'thumbnails')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './sessions'