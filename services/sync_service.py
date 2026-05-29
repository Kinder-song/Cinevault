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
                db_size = row.get('size_bytes')
                db_mtime = row.get('updated_at').timestamp() if row.get('updated_at') else 0

                if db_size == file_size and abs(db_mtime - file_mtime) < 1:
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
                            filepath = %s,
                            size_bytes = %s,
                            duration = %s,
                            width = %s,
                            height = %s,
                            codec = %s,
                            bitrate = %s,
                            framerate = %s
                        WHERE filename = %s
                        """,
                        (title, video_path_full, file_size, duration, width,
                         height, codec, bitrate, fps, filename)
                    )
                else:
                    # Insert new record (user_id defaults to 1 for admin)
                    cursor.execute(
                        """
                        INSERT INTO videos (
                            user_id, title, filename, filepath, size_bytes,
                            duration, width, height, codec, bitrate, framerate
                        ) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (title, filename, video_path_full, file_size, duration,
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
        List of all video rows as dicts.
    """
    try:
        with with_db_cursor() as cursor:
            cursor.execute("SELECT * FROM videos ORDER BY filename")
            rows = cursor.fetchall()
            return [video_dict_from_row(row) for row in rows]
    except Exception as e:
        sync_logger.error(f"Error fetching all videos from DB: {e}")
        return []


def sync_and_get_videos(video_path: str) -> List[Dict[str, Any]]:
    """Sync video directory with database and return all videos.

    Args:
        video_path: Path to the video directory.

    Returns:
        List of all videos from database after sync.
    """
    files_on_disk: Dict[str, str] = {}

    # Scan video directory for video files
    if os.path.isdir(video_path):
        for entry in os.scandir(video_path):
            if entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    files_on_disk[entry.name] = entry.path

    sync_logger.info(f"Found {len(files_on_disk)} video files on disk")

    # Get existing DB records
    existing_records: Dict[str, Dict[str, Any]] = {}
    try:
        with with_db_cursor() as cursor:
            cursor.execute("SELECT filename, size_bytes, updated_at FROM videos")
            for row in cursor.fetchall():
                existing_records[row['filename']] = row
    except Exception as e:
        sync_logger.error(f"Error fetching existing DB records: {e}")

    # Determine which files need sync
    for filename, filepath in files_on_disk.items():
        file_stat = os.stat(filepath)
        file_size = file_stat.st_size
        file_mtime = file_stat.st_mtime

        needs_sync = True
        if filename in existing_records:
            db_record = existing_records[filename]
            db_size = db_record.get('size_bytes')
            db_mtime = db_record.get('updated_at').timestamp() if db_record.get('updated_at') else 0

            # Skip if file size and mtime match
            if db_size == file_size and abs(db_mtime - file_mtime) < 1:
                needs_sync = False
                sync_logger.debug(f"Skipping unchanged file: {filename}")

        if needs_sync:
            sync_logger.info(f"Syncing: {filename}")
            sync_video_to_db(filename, filepath)

    # Return all videos from DB
    return get_all_videos_from_db()