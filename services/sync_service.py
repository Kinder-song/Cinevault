"""Sync service for video library synchronization."""

import os
from typing import Any, Dict, List, Optional

from services.video_service import (
    VIDEO_EXTENSIONS,
    extract_metadata,
    generate_thumbnail,
    video_dict_from_row,
)
from services.db_service import get_db_connection, with_db_cursor
from services.library_cache import LibraryCache
from utils.logger import sync_logger


def sync_video_to_db(filename: str, video_path_full: str) -> Optional[Dict[str, Any]]:
    """Check if video needs sync and update/insert into database.

    Args:
        filename: Video filename.
        video_path_full: Full path to the video file.

    Returns:
        Database row as dict, or None if failed.
    """
    if not os.path.isfile(video_path_full):
        sync_logger.warning(f"Video file not found: {video_path_full}")
        return None

    file_stat = os.stat(video_path_full)
    file_size = file_stat.st_size
    file_mtime = file_stat.st_mtime

    try:
        with with_db_cursor() as cursor:
            # Check if video exists in DB
            cursor.execute(
                "SELECT * FROM videos WHERE filename = %s",
                (filename,)
            )
            row = cursor.fetchone()

            if row:
                # Check if sync is needed (compare size and mtime)
                db_size = row.get('file_size')
                db_mtime = row.get('file_mtime', 0)

                if db_size == file_size and db_mtime == int(file_mtime):
                    sync_logger.debug(f"Video unchanged, skipping: {filename}")
                    return video_dict_from_row(row)

            # Needs sync - extract metadata and generate thumbnail
            metadata = extract_metadata(video_path_full)
            thumbnail_path = generate_thumbnail(
                os.path.splitext(filename)[0],
                video_path_full
            )

            title = os.path.splitext(filename)[0]
            duration = metadata.get('duration')
            width = metadata.get('width')
            height = metadata.get('height')
            fps = metadata.get('fps')
            bitrate = metadata.get('bitrate')
            codec = metadata.get('codec')

            with with_db_cursor() as cursor:
                if row:
                    # Update existing record
                    cursor.execute(
                        """
                        UPDATE videos SET
                            title = %s,
                            file_size = %s,
                            duration = %s,
                            width = %s,
                            height = %s,
                            codec = %s,
                            bitrate = %s,
                            fps = %s
                        WHERE filename = %s
                        """,
                        (title, file_size, duration, width,
                         height, codec, bitrate, fps, filename)
                    )
                else:
                    # Insert new record (user_id defaults to 1 for admin)
                    cursor.execute(
                        """
                        INSERT INTO videos (
                            filename, title, file_size,
                            duration, width, height, codec, bitrate, fps
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (filename, title, file_size, duration,
                         width, height, codec, bitrate, fps)
                    )

                # Fetch the updated/inserted row
                cursor.execute(
                    "SELECT * FROM videos WHERE filename = %s",
                    (filename,)
                )
                result_row = cursor.fetchone()

            sync_logger.info(f"Synced video to DB: {filename}")
            return video_dict_from_row(result_row) if result_row else None

    except Exception as e:
        sync_logger.error(f"Error syncing video {filename}: {e}")
        return None


def get_all_videos_from_db() -> List[Dict[str, Any]]:
    """Get all videos from database.

    Returns:
        List of all video rows as dicts (raw, not converted).
    """
    try:
        with with_db_cursor() as cursor:
            cursor.execute("SELECT * FROM videos ORDER BY filename")
            return cursor.fetchall()
    except Exception as e:
        sync_logger.error(f"Error fetching all videos from DB: {e}")
        return []


# Module-level cache registry, keyed by absolute video_dir path.
_cache_registry: dict = {}


def _get_cache(video_path: str) -> LibraryCache:
    """Get or create a LibraryCache for the given video directory."""
    cache = _cache_registry.get(video_path)
    if cache is None:
        cache = LibraryCache(video_path)
        _cache_registry[video_path] = cache
    return cache


def sync_and_get_videos(video_path: str) -> List[Dict[str, Any]]:
    """Sync video directory with database and return all videos.

    Performs an incremental scan: only files whose ``(size, mtime)`` changed
    since the last call are ffmpeg-probed. The LibraryCache is the source of
    truth for "what was scanned last time" — a file is skipped when its
    cached ``(size, mtime)`` still matches the current scan. The DB is
    only consulted to verify the file made it in (defends against prior
    sync failures). Use ``_cache_registry.clear()`` to force a full
    resync (e.g., in tests).
    """
    cache = _get_cache(video_path)
    # Snapshot the previous cache state before scan() overwrites it
    previous_state = dict(cache._cache)
    files_on_disk = cache.scan()

    sync_logger.info(f"Found {len(files_on_disk)} video files on disk")

    # Get existing DB filenames to detect prior-sync failures
    db_filenames: set = set()
    try:
        with with_db_cursor() as cursor:
            cursor.execute("SELECT filename FROM videos")
            for row in cursor.fetchall():
                db_filenames.add(row["filename"])
    except Exception as e:
        sync_logger.error("Error fetching existing DB records: %s", e)

    for filename, meta in files_on_disk.items():
        prev = previous_state.get(filename)
        unchanged = (
            prev is not None
            and prev["size"] == meta["size"]
            and prev["mtime"] == meta["mtime"]
        )
        if unchanged and filename in db_filenames:
            sync_logger.debug("Skipping unchanged file: %s", filename)
            continue
        sync_logger.info("Syncing: %s", filename)
        sync_video_to_db(filename, meta["path"])

    return get_all_videos_from_db()