import os
import subprocess
import random
import json
from config import Config

THUMBNAIL_DIR = 'thumbnails'

def ensure_thumbnail_dir():
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)

def generate_thumbnail(filename, refresh=False):
    """Generate thumbnail for video, returns thumbnail path or None"""
    ensure_thumbnail_dir()

    video_path = os.path.join(Config.VIDEO_PATH, filename)
    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumbnail_path = os.path.join(THUMBNAIL_DIR, thumb_name)

    # If thumbnail exists and not refreshing, return existing
    if os.path.exists(thumbnail_path) and not refresh:
        return thumbnail_path

    # Random time point between 0.5s and 10% of video duration
    duration = get_video_duration(video_path)
    if not duration:
        return None

    max_time = min(10, duration * 0.1)
    random_time = random.uniform(0.5, max(1, max_time))

    cmd = [
        Config.FFMPEG_PATH, '-y',
        '-ss', str(random_time),
        '-i', video_path,
        '-vframes', '1',
        '-q:v', '2',
        thumbnail_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=30)
        if os.path.exists(thumbnail_path):
            return thumbnail_path
    except:
        pass

    return None

def get_video_duration(filepath):
    """Get video duration in seconds using ffmpeg"""
    cmd = [
        Config.FFMPEG_PATH,
        '-i', filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # Parse Duration from output: "Duration: 00:00:24.68"
        for line in result.stderr.split('\n'):
            if 'Duration:' in line:
                # Extract time portion: "00:00:24.68"
                time_part = line.split('Duration:')[1].split(',')[0].strip()
                parts = time_part.split(':')
                if len(parts) == 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    return hours * 3600 + minutes * 60 + int(seconds)
                elif len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + int(seconds)
    except:
        pass
    return None