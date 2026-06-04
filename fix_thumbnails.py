"""One-shot self-heal for thumbnail inconsistencies.

Run: python3 fix_thumbnails.py [--regen-missing] [--cleanup-legacy]

What it does:
  1. For every row in `videos` with thumbnail_path:
     - If the file at the path is missing but `video/<filename>` exists:
       - First, try to move it from `video/thumbnails/` (legacy location)
       - Otherwise, regenerate via ffmpeg
  2. If --cleanup-legacy is passed, delete the now-unused `video/thumbnails/`.
  3. If --regen-missing is passed, regenerate every thumbnail that is missing
     (even if no legacy file is around).
"""
import argparse
import os
import shutil
import sys

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

from config import Config
from services.video_service import generate_thumbnail
from utils.logger import db_logger


def all_videos():
    conn = mysql.connector.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, filename, title, thumbnail_path FROM videos ORDER BY filename")
    for row in cur.fetchall():
        yield conn, cur, row


def fix_one(conn, cur, row, regen_missing):
    filename = row["filename"]
    title = row["title"] or filename
    thumb_path = os.path.join(Config.THUMBNAIL_DIR,
                              f"{os.path.splitext(os.path.basename(filename))[0]}.jpg")
    video_path = os.path.join(Config.VIDEO_PATH, filename)

    if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
        return "ok"

    if not os.path.exists(video_path):
        print(f"  ⚠️  {title}: source video missing at {video_path}, skip")
        return "missing-source"

    # 1) Try legacy location: video/thumbnails/<basename>.jpg
    legacy_dir = os.path.join(os.path.dirname(video_path), "thumbnails")
    legacy_path = os.path.join(legacy_dir,
                               f"{os.path.splitext(os.path.basename(filename))[0]}.jpg")
    if os.path.exists(legacy_path) and os.path.getsize(legacy_path) > 0:
        try:
            os.makedirs(Config.THUMBNAIL_DIR, exist_ok=True)
            shutil.move(legacy_path, thumb_path)
            print(f"  🔁  {title}: moved {legacy_path} -> {thumb_path}")
            return "moved"
        except OSError as e:
            print(f"  ⚠️  {title}: move failed ({e}); will regenerate")

    # 2) Regenerate
    if regen_missing or not os.path.exists(thumb_path):
        new_thumb = generate_thumbnail(
            os.path.splitext(os.path.basename(filename))[0],
            video_path,
        )
        if new_thumb and os.path.exists(new_thumb):
            try:
                cur.execute(
                    "UPDATE videos SET thumbnail_path = %s WHERE id = %s",
                    (new_thumb, row["id"]),
                )
                conn.commit()
                print(f"  ✨  {title}: regenerated -> {new_thumb}")
                return "regenerated"
            except mysql.connector.Error as e:
                print(f"  ⚠️  {title}: regenerated but DB update failed ({e})")
                return "regenerated-no-db"
        print(f"  ❌  {title}: ffmpeg failed to regenerate")
        return "ffmpeg-failed"

    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regen-missing", action="store_true",
                    help="Regenerate any missing thumbnail from scratch (not just move from legacy)")
    ap.add_argument("--cleanup-legacy", action="store_true",
                    help="Delete the now-unused video/thumbnails/ directory at the end")
    args = ap.parse_args()

    counts = {"ok": 0, "moved": 0, "regenerated": 0,
              "regenerated-no-db": 0, "missing-source": 0,
              "ffmpeg-failed": 0, "unknown": 0}

    for conn, cur, row in all_videos():
        result = fix_one(conn, cur, row, args.regen_missing)
        counts[result] = counts.get(result, 0) + 1
    cur.close()
    conn.close()

    print("\n=== Summary ===")
    for k, v in counts.items():
        if v:
            print(f"  {k:20s} {v}")
    print(f"  {'TOTAL':20s} {sum(counts.values())}")

    if args.cleanup_legacy:
        legacy = os.path.join(Config.VIDEO_PATH, "thumbnails")
        if os.path.isdir(legacy):
            try:
                shutil.rmtree(legacy)
                print(f"\n🧹  Removed legacy dir {legacy}")
            except OSError as e:
                print(f"\n⚠️  Could not remove {legacy}: {e}")
        else:
            print(f"\n🧹  No legacy dir at {legacy}, nothing to clean")

    if counts.get("ffmpeg-failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
