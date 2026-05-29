"""CineVault database service module."""

from services.db_service import (
    db_pool,
    get_db_connection,
    init_database,
    with_db_cursor,
    get_dashboard_stats,
)

__all__ = [
    "db_pool",
    "get_db_connection",
    "init_database",
    "with_db_cursor",
    "get_dashboard_stats",
]