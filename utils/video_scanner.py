import os
import subprocess
import json
from config import Config

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v'}

def get_video_duration(filepath):
    """Get video duration in seconds using ffprobe"""
    cmd = [
        Config.FFMPEG_PATH, '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'json',
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return int(float(data['format']['duration']))
    except:
        return None

def format_duration(seconds):
    """Format seconds to MM:SS or HH:MM:SS"""
    if not seconds:
        return None
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def format_filesize(size_bytes):
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"

def scan_videos():
    """Scan video directory and return list of video info"""
    video_path = Config.VIDEO_PATH
    if not os.path.exists(video_path):
        return []

    videos = []
    for filename in os.listdir(video_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in VIDEO_EXTENSIONS:
            continue

        filepath = os.path.join(video_path, filename)
        stat = os.stat(filepath)

        videos.append({
            'filename': filename,
            'title': os.path.splitext(filename)[0],
            'size': stat.st_size,
            'size_formatted': format_filesize(stat.st_size),
            'duration': get_video_duration(filepath),
            'duration_formatted': format_duration(get_video_duration(filepath))
        })

    return videos