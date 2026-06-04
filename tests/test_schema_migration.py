"""Verify new tables exist after init_database()."""
import os
import pytest

from services.db_service import init_database


@pytest.mark.skipif(not os.getenv("INTEGRATION_DB"), reason="Real DB required")
def test_comments_table_exists():
    init_database()
    import mysql.connector
    conn = mysql.connector.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )
    cur = conn.cursor()
    cur.execute("SHOW TABLES LIKE 'comments'")
    assert cur.fetchone() is not None
    cur.execute("SHOW TABLES LIKE 'watch_history'")
    assert cur.fetchone() is not None
