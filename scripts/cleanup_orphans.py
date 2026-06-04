"""Remove orphan video records (DB row exists but file is missing on disk).

Run: python3 scripts/cleanup_orphans.py [--dry-run]

Use after a video file is deleted from the filesystem, or periodically
to detect sync drift. CASCADE on videos.id cleans up video_tags,
watch_history, collection_videos, and comments automatically.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.db_service import with_db_cursor
from utils.logger import db_logger


def find_orphans():
    """Return list of (id, filename) for DB rows whose file is missing."""
    orphans = []
    with with_db_cursor() as cur:
        cur.execute("SELECT id, filename FROM videos")
        rows = cur.fetchall()
    for r in rows:
        fp = os.path.join(Config.VIDEO_PATH, r["filename"])
        if not os.path.exists(fp):
            orphans.append((r["id"], r["filename"]))
    return orphans


def delete_orphans(orphans):
    """Delete the given orphan rows in one transaction."""
    if not orphans:
        return 0
    ids = [o[0] for o in orphans]
    placeholders = ",".join(["%s"] * len(ids))
    with with_db_cursor() as cur:
        cur.execute(f"DELETE FROM videos WHERE id IN ({placeholders})", ids)
        return cur.rowcount


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List orphans without deleting them",
    )
    args = parser.parse_args()

    orphans = find_orphans()
    if not orphans:
        print("No orphans found.")
        return 0

    print(f"Found {len(orphans)} orphan video(s):")
    for vid, fn in orphans:
        print(f"  id={vid:5}  {fn}")

    if args.dry_run:
        print("\n--dry-run: no changes made.")
        return 0

    deleted = delete_orphans(orphans)
    db_logger.info("cleanup_orphans: deleted %d rows", deleted)
    print(f"\nDeleted {deleted} orphan row(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
