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


def _empty_metadata() -> Dict[str, Any]:
    return {
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


def _parse_ffmpeg_stderr(stderr: str) -> Dict[str, Any]:
    """Parse ffmpeg stderr output for video metadata.

    Returns a dict with keys: duration, width, height, fps, bitrate, codec,
    audio_codec, audio_channels, audio_sample_rate. Missing values are None.
    """
    result = _empty_metadata()

    # Parse Duration
    duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', stderr)
    if duration_match:
        h, m, s, cs = duration_match.groups()
        result['duration'] = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

    # Parse resolution (e.g., "1920x1080 [SAR")
    video_stream_match = re.search(r'(\d+)x(\d+)\s+\[SAR', stderr)
    if video_stream_match:
        result['width'] = int(video_stream_match.group(1))
        result['height'] = int(video_stream_match.group(2))

    # Codec
    codec_match = re.search(r'Video:\s*(\w+)', stderr)
    if codec_match:
        result['codec'] = codec_match.group(1)

    # FPS
    fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', stderr)
    if fps_match:
        result['fps'] = float(fps_match.group(1))

    # Bitrate
    bitrate_match = re.search(r'bitrate:\s*(\d+)\s*kb/s', stderr)
    if bitrate_match:
        result['bitrate'] = int(bitrate_match.group(1))

    # Audio
    audio_stream_match = re.search(
        r'Stream.*Audio:\s*(\w+).*?(?:(\d+)\s*Hz.*?)?(?:,?\s*(\d+)\s*channels)?',
        stderr,
    )
    if audio_stream_match:
        result['audio_codec'] = audio_stream_match.group(1)
        if audio_stream_match.group(2):
            result['audio_sample_rate'] = int(audio_stream_match.group(2))
        if audio_stream_match.group(3):
            result['audio_channels'] = int(audio_stream_match.group(3))
    else:
        audio_match = re.search(r'Stream.*Audio:\s*(\w+)', stderr)
        if audio_match:
            result['audio_codec'] = audio_match.group(1)

    return result


def extract_metadata(filepath: str) -> Dict[str, Any]:
    """Extract video metadata using ffmpeg.

    Args:
        filepath: Full path to the video file.

    Returns:
        Dictionary with duration, width, height, fps, bitrate, codec,
        audio_codec, audio_channels, audio_sample_rate.
    """
    try:
        proc = subprocess.run(
            [Config.FFMPEG_PATH, '-i', filepath],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            timeout=15,
        )
        stderr = proc.stderr.decode('utf-8', errors='replace')
        return _parse_ffmpeg_stderr(stderr)
    except subprocess.TimeoutExpired:
        db_logger.warning(f"Timeout extracting metadata from {filepath}")
        return _empty_metadata()
    except Exception as e:
        db_logger.error(f"Error extracting metadata from {filepath}: {e}")
        return _empty_metadata()


def generate_thumbnail(filename: str, video_path_full: str) -> Optional[str]:
    """Generate a jpg thumbnail from a video.

    Writes the thumbnail to ``Config.THUMBNAIL_DIR`` (default ``thumbnails/``,
    relative to the working directory) and returns the same path string that
    the /thumbnail/<f> route serves from — so the two stay in sync.

    Args:
        filename: Base filename for the thumbnail (without extension).
        video_path_full: Full path to the video file.

    Returns:
        Relative path like ``thumbnails/<basename>.jpg`` on success, or
        ``None`` if ffmpeg failed / timed out.
    """
    if not filename or not video_path_full:
        db_logger.error("generate_thumbnail: missing filename or video_path_full")
        return None

    # Strip any path separators from filename to keep it as a bare basename
    safe_basename = os.path.basename(filename)
    thumbnail_dir = Config.THUMBNAIL_DIR
    thumbnail_path = os.path.join(thumbnail_dir, f"{safe_basename}.jpg")
    relative_path = f"{thumbnail_dir}/{safe_basename}.jpg"

    # Ensure thumbnail directory exists
    try:
        os.makedirs(thumbnail_dir, exist_ok=True)
    except OSError as e:
        db_logger.error(f"Cannot create thumbnail dir {thumbnail_dir}: {e}")
        return None

    # Get video duration for seek time. ffmpeg prints info to stderr; we use
    # the same parsing as the metadata extractor.
    duration = None
    try:
        probe = subprocess.run(
            [Config.FFMPEG_PATH, '-i', video_path_full],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            timeout=15,
        )
        stderr = probe.stderr.decode('utf-8', errors='replace')
        duration_match = re.search(
            r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', stderr
        )
        if duration_match:
            h, m, s, cs = duration_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
    except subprocess.TimeoutExpired:
        db_logger.warning(f"Timeout probing duration for {filename}")
    except FileNotFoundError:
        db_logger.error(f"ffmpeg not found at {Config.FFMPEG_PATH}")
        return None
    except Exception as e:
        db_logger.warning(f"Error probing duration for {filename}: {e}")

    # Calculate seek time: 0.5 to min(10, duration*0.1)
    if duration and duration > 0:
        max_seek = min(10, duration * 0.1)
        seek_time = random.uniform(0.5, max(0.5, max_seek))
    else:
        seek_time = 0.5

    # Run the actual frame extraction
    try:
        result = subprocess.run(
            [
                Config.FFMPEG_PATH,
                '-ss', str(seek_time),
                '-i', video_path_full,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                thumbnail_path,
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            timeout=30,
        )
        if result.returncode != 0:
            err = result.stderr.decode('utf-8', errors='replace')[-300:]
            db_logger.error(
                f"ffmpeg failed (rc={result.returncode}) for {filename}: {err}"
            )
            # Clean up partial file if any
            if os.path.exists(thumbnail_path):
                try:
                    os.remove(thumbnail_path)
                except OSError:
                    pass
            return None

        if os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0:
            return relative_path

        db_logger.error(
            f"ffmpeg exited 0 but no thumbnail at {thumbnail_path} for {filename}"
        )
        return None
    except subprocess.TimeoutExpired:
        db_logger.warning(f"Timeout generating thumbnail for {filename}")
        if os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except OSError:
                pass
        return None
    except FileNotFoundError:
        db_logger.error(f"ffmpeg not found at {Config.FFMPEG_PATH}")
        return None
    except Exception as e:
        db_logger.error(f"Error generating thumbnail for {filename}: {e}")
        return None


def probe_and_thumbnail(
    filepath: str, safe_basename: str
) -> tuple[Dict[str, Any], str | None]:
    """Run ffmpeg ONCE to extract a thumbnail and parse its stderr for metadata.

    This replaces the previous 3-call pattern (probe duration + extract
    metadata + extract frame) with a single ffmpeg invocation. The frame
    extraction command's stderr contains all the info we need.

    Args:
        filepath: Absolute path to the source video.
        safe_basename: Filename without extension (used for thumbnail name).

    Returns:
        (metadata_dict, thumbnail_relative_path) on success.
        ({}, None) if ffmpeg failed or timed out.
    """
    thumbnail_dir = Config.THUMBNAIL_DIR
    thumbnail_path = os.path.join(thumbnail_dir, f"{safe_basename}.jpg")
    relative_path = f"{thumbnail_dir}/{safe_basename}.jpg"

    try:
        os.makedirs(thumbnail_dir, exist_ok=True)
    except OSError as e:
        db_logger.error("Cannot create thumbnail dir %s: %s", thumbnail_dir, e)
        return ({}, None)

    # Seek to 5 seconds (fast keyframe-based seek; ffmpeg will pick the
    # nearest earlier keyframe for MP4/MKV). If the video is shorter than
    # 5s, the seek will be clamped automatically.
    seek_time = 5

    try:
        proc = subprocess.run(
            [
                Config.FFMPEG_PATH,
                "-ss", str(seek_time),
                "-i", filepath,
                "-vframes", "1",
                "-q:v", "2",
                "-y", thumbnail_path,
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        db_logger.warning("Timeout generating thumbnail for %s", safe_basename)
        if os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except OSError:
                pass
        return ({}, None)
    except FileNotFoundError:
        db_logger.error("ffmpeg not found at %s", Config.FFMPEG_PATH)
        return ({}, None)
    except Exception as e:
        db_logger.error("Error running ffmpeg for %s: %s", safe_basename, e)
        return ({}, None)

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")[-300:]
        db_logger.error(
            "ffmpeg failed (rc=%s) for %s: %s", proc.returncode, safe_basename, err
        )
        if os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except OSError:
                pass
        return ({}, None)

    if not (os.path.exists(thumbnail_path) and os.path.getsize(thumbnail_path) > 0):
        db_logger.error(
            "ffmpeg exited 0 but no thumbnail at %s for %s",
            thumbnail_path, safe_basename,
        )
        return ({}, None)

    # The same stderr output has all the metadata. Reuse the existing parser.
    stderr_text = proc.stderr.decode("utf-8", errors="replace")
    metadata = _parse_ffmpeg_stderr(stderr_text)
    return metadata, relative_path


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
        'filesize': format_filesize(row.get('file_size') or 0),
        'size_bytes': row.get('file_size'),
        'duration': format_duration(row.get('duration')),
        'duration_formatted': format_duration(row.get('duration')),
        'duration_raw': row.get('duration'),
        'width': row.get('width'),
        'height': row.get('height'),
        'resolution': f"{row.get('width', 0)}x{row.get('height', 0)}",
        'codec': row.get('codec'),
        'bitrate': format_bitrate(row.get('bitrate')),
        'bitrate_raw': row.get('bitrate'),
        'fps': format_fps(row.get('fps')),
        'fps_raw': row.get('fps'),
        'thumbnail': row.get('thumbnail_path'),  # thumbnail path for template
        # DB column is `favorite` and `watched_duration`; expose both old and new
        # names so Jinja templates using either still work.
        'favorite': row.get('favorite', False),
        'is_favorite': row.get('favorite', False),
        'rating': row.get('rating', 0),
        'progress': row.get('watched_duration'),
        'watched_duration': format_duration(row.get('watched_duration')),
        'last_watched': None,
        'created_at': row.get('created_at'),
        'created': row.get('created_at'),  # alias for template compatibility
        'size': row.get('file_size') or 0,  # alias for template compatibility
    }