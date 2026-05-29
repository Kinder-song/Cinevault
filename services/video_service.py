"""Video service for metadata extraction, thumbnails, and file scanning."""

import os
import random
import re
import subprocess
from typing import Any, Dict, List, Optional

from config import Config
from utils.logger import db_logger
from utils.formatters import format_duration, format_bitrate, format_fps, format_filesize

# Constants
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v'}
VIDEO_MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.mkv': 'video/x-matroska',
    '.webm': 'video/webm',
    '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo',
    '.m4v': 'video/x-m4v',
}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass'}


def extract_metadata(filepath: str) -> Dict[str, Any]:
    """Extract video metadata using ffmpeg.

    Args:
        filepath: Full path to the video file.

    Returns:
        Dictionary with duration, width, height, fps, bitrate, codec,
        audio_codec, audio_channels, audio_sample_rate.
    """
    result = {
        'duration': None,
        'width': None,
        'height': None,
        'fps': None,
        'bitrate': None,
        'codec': None,
        'audio_codec': None,
        'audio_channels': None,
        'audio_sample_rate': None,
    }

    try:
        cmd = [Config.FFMPEG_PATH, '-i', filepath]
        proc = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            timeout=15
        )
        stderr = proc.stderr.decode('utf-8', errors='replace')

        # Parse Duration
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', stderr)
        if duration_match:
            h, m, s, cs = duration_match.groups()
            result['duration'] = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

        # Parse Video stream info
        video_stream_match = re.search(
            r'Stream.*Video:\s*(\w+).*?(\d+)x(\d+).*?(\d+(?:\.\d+)?)\s*fps',
            stderr
        )
        if video_stream_match:
            result['codec'] = video_stream_match.group(1)
            result['width'] = int(video_stream_match.group(2))
            result['height'] = int(video_stream_match.group(3))
            result['fps'] = float(video_stream_match.group(4))
        else:
            # Try simpler pattern
            stream_match = re.search(r'Stream.*Video:\s*(\w+)', stderr)
            if stream_match:
                result['codec'] = stream_match.group(1)
            dim_match = re.search(r'(\d{2,5})x(\d{2,5})', stderr)
            if dim_match:
                result['width'] = int(dim_match.group(1))
                result['height'] = int(dim_match.group(2))
            fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', stderr)
            if fps_match:
                result['fps'] = float(fps_match.group(1))

        # Parse bitrate
        bitrate_match = re.search(r'bitrate:\s*(\d+)\s*kb/s', stderr)
        if bitrate_match:
            result['bitrate'] = int(bitrate_match.group(1))

        # Parse Audio stream info
        audio_stream_match = re.search(
            r'Stream.*Audio:\s*(\w+).*?(?:(\d+)\s*Hz.*?)?(?:,?\s*(\d+)\s*channels)?',
            stderr
        )
        if audio_stream_match:
            result['audio_codec'] = audio_stream_match.group(1)
            if audio_stream_match.group(2):
                result['audio_sample_rate'] = int(audio_stream_match.group(2))
            if audio_stream_match.group(3):
                result['audio_channels'] = int(audio_stream_match.group(3))
        else:
            # Try simpler audio pattern
            audio_match = re.search(r'Stream.*Audio:\s*(\w+)', stderr)
            if audio_match:
                result['audio_codec'] = audio_match.group(1)

    except subprocess.TimeoutExpired:
        db_logger.warning(f"Timeout extracting metadata from {filepath}")
    except Exception as e:
        db_logger.error(f"Error extracting metadata from {filepath}: {e}")

    return result


def generate_thumbnail(filename: str, video_path_full: str) -> Optional[str]:
    """Generate a jpg thumbnail from a video.

    Args:
        filename: Base filename for the thumbnail (without extension).
        video_path_full: Full path to the video file.

    Returns:
        Path to generated thumbnail (relative), or None if generation failed.
    """
    thumbnail_dir = os.path.join(os.path.dirname(video_path_full), 'thumbnails')
    thumbnail_path = os.path.join(thumbnail_dir, f"{filename}.jpg")

    # Ensure thumbnail directory exists
    os.makedirs(thumbnail_dir, exist_ok=True)

    # Get video duration for thumbnail seek time
    duration = None
    try:
        cmd = [Config.FFMPEG_PATH, '-i', video_path_full]
        proc = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            timeout=15
        )
        stderr = proc.stderr.decode('utf-8', errors='replace')
        duration_match = re.search(
            r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', stderr
        )
        if duration_match:
            h, m, s, cs = duration_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
    except Exception:
        pass

    # Calculate seek time: 0.5 to min(10, duration*0.1)
    if duration:
        max_seek = min(10, duration * 0.1)
        seek_time = random.uniform(0.5, max(0.5, max_seek))
    else:
        seek_time = 0.5

    try:
        cmd = [
            Config.FFMPEG_PATH,
            '-ss', str(seek_time),
            '-i', video_path_full,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            thumbnail_path
        ]
        subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, timeout=30)
        if os.path.exists(thumbnail_path):
            # Return relative path
            return f"thumbnails/{filename}.jpg"
    except subprocess.TimeoutExpired:
        db_logger.warning(f"Timeout generating thumbnail for {filename}")
    except Exception as e:
        db_logger.error(f"Error generating thumbnail for {filename}: {e}")

    return None


def scan_subtitles(filename: str, video_dir: str) -> List[Dict[str, Any]]:
    """Scan for subtitle files matching the video filename.

    Args:
        filename: Video filename (with extension) to match.
        video_dir: Directory to scan for subtitles.

    Returns:
        List of dicts with {filename, ext, label} for each subtitle file.
    """
    subtitles = []
    base_name = os.path.splitext(filename)[0]

    if not os.path.isdir(video_dir):
        return subtitles

    for entry in os.scandir(video_dir):
        if not entry.is_file():
            continue
        entry_name = os.path.splitext(entry.name)[0]
        entry_ext = os.path.splitext(entry.name)[1].lower()
        if entry_ext in SUBTITLE_EXTENSIONS and entry_name.startswith(base_name):
            label = entry_ext.upper().replace('.', '')
            subtitles.append({
                'filename': entry.name,
                'ext': entry_ext,
                'label': f"{label} ({entry.name})"
            })

    return subtitles


def scan_screenshots(filename: str, video_dir: str) -> List[Dict[str, Any]]:
    """Scan for image files matching the video filename pattern.

    Args:
        filename: Video filename (with extension) to match.
        video_dir: Directory to scan for screenshots.

    Returns:
        List of dicts with {filename, path} for each screenshot.
    """
    screenshots = []
    base_name = os.path.splitext(filename)[0]

    if not os.path.isdir(video_dir):
        return screenshots

    for entry in os.scandir(video_dir):
        if not entry.is_file():
            continue
        entry_name = os.path.splitext(entry.name)[0]
        entry_ext = os.path.splitext(entry.name)[1].lower()
        if entry_ext in IMAGE_EXTENSIONS and entry_name.startswith(base_name):
            screenshots.append({
                'filename': entry.name,
                'path': os.path.join(video_dir, entry.name)
            })

    return screenshots


def video_dict_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a database row to a video dictionary with formatted fields.

    Args:
        row: Database row dictionary.

    Returns:
        Dictionary with formatted video information.
    """
    return {
        'id': row.get('id'),
        'title': row.get('title'),
        'filename': row.get('filename'),
        'filepath': row.get('filepath'),
        'filesize': format_filesize(row.get('size_bytes') or 0),
        'size_bytes': row.get('size_bytes'),
        'duration': format_duration(row.get('duration')),
        'duration_raw': row.get('duration'),
        'width': row.get('width'),
        'height': row.get('height'),
        'resolution': f"{row.get('width', 0)}x{row.get('height', 0)}",
        'codec': row.get('codec'),
        'bitrate': format_bitrate(row.get('bitrate')),
        'bitrate_raw': row.get('bitrate'),
        'fps': format_fps(row.get('framerate')),
        'fps_raw': row.get('framerate'),
        'favorite': row.get('favorite', False),
        'watched_duration': format_duration(row.get('watched_duration')),
        'last_watched': row.get('last_watched'),
        'created_at': row.get('created_at'),
    }