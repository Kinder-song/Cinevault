import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'cinevault-secret-key-change-in-production')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'video')
    VIDEO_PATH = os.getenv('video_path', './video')
    FFMPEG_PATH = os.getenv('FFMPEG_PATH', './ffmpeg')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './sessions'