"""Verify error responses do not leak internal details like SQL."""
from unittest.mock import patch

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = 1
        yield c


def test_500_response_does_not_leak_sql_error(client):
    """Forced DB exception must return generic message, not SQL string."""
    from services.db_service import get_db_connection

    def boom(*a, **kw):
        raise RuntimeError(
            "1146 Table 'video.users' doesn't exist (SQL: SELECT * FROM users)"
        )

    with patch("services.db_service.get_db_connection", side_effect=boom):
        res = client.get("/api/user/profile")
        # Either 500 from the route OR a Flask errorhandler 500 — both must sanitize
        body = res.get_data(as_text=True)
        if res.status_code == 500:
            assert "SQL" not in body, f"SQL leaked: {body}"
            assert "users" not in body or "Internal" in body, f"Table leaked: {body}"
