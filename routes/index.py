"""Index page (video gallery).

The gallery is the application's landing page after login. It paginates the
result of ``sync_and_get_videos`` and decorates each card with its tags and
the available collections (used by the filter dropdown).
"""

from flask import Blueprint, render_template, request, session

from repositories.collection_repo import CollectionRepository
from repositories.history_repo import HistoryRepository
from repositories.tag_repo import TagRepository
from services.db_service import with_db_cursor
from services.sync_service import sync_and_get_videos
from services.video_service import video_dict_from_row
from utils.logger import video_logger
from routes.auth import login_required
from routes.player import get_user_video_path

index_bp = Blueprint("index", __name__)


@index_bp.route("/")
@login_required
def index():
    """Video gallery page with server-side pagination."""
    video_path = get_user_video_path(session["user_id"])
    db_rows = sync_and_get_videos(video_path)
    all_videos = [video_dict_from_row(r) for r in db_rows]

    # Server-side pagination (clamp per_page to 12-96).
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 24, type=int)
    per_page = min(max(per_page, 12), 96)
    total = len(all_videos)
    total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
    page = min(max(page, 1), total_pages)
    start = (page - 1) * per_page
    videos = all_videos[start:start + per_page]

    tags_by_video: dict = {}
    collections: list = []
    recent: list = []
    try:
        with with_db_cursor() as cursor:
            tags_by_video = TagRepository(cursor).list_tags_by_video()
            collections = CollectionRepository(cursor).list_all()
            recent = HistoryRepository(cursor).list_recent(
                user_id=session["user_id"], limit=6
            )
    except Exception as e:
        video_logger.error(f"Error loading tags/collections for index: {e}")

    return render_template(
        "index.html",
        videos=videos,
        tags_by_video=tags_by_video,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        total=total,
        collections=collections,
        recent=recent,
    )
