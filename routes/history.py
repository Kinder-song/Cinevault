"""Watch history page."""
from flask import Blueprint, render_template, session

from repositories.history_repo import HistoryRepository
from services.db_service import with_db_cursor
from routes.auth import login_required

history_bp = Blueprint("history", __name__)


@history_bp.route("/history")
@login_required
def history_page():
    with with_db_cursor() as cursor:
        items = HistoryRepository(cursor).list_recent(
            user_id=session["user_id"], limit=100
        )
    return render_template("history.html", items=items)
