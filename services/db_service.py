"""Database service for CineVault with MySQL connection pooling."""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import pooling

from config import Config
from utils.logger import db_logger

# Global connection pool
db_pool: Optional[pooling.MySQLConnectionPool] = None


def _init_db_pool() -> Optional[pooling.MySQLConnectionPool]:
    """Create and return MySQL connection pool.

    Returns:
        MySQLConnectionPool instance or None if connection fails.
    """
    global db_pool
    try:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="cinevault_pool",
            pool_size=8,
            pool_reset_session=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
        )
        db_logger.info("Database connection pool initialized successfully")
        return db_pool
    except mysql.connector.Error as e:
        db_logger.error(f"Failed to initialize database pool: {e}")
        return None


def get_db_connection():
    """Get a connection from the pool.

    Returns:
        MySQL connection from pool.
    """
    global db_pool
    if db_pool is None:
        _init_db_pool()
    return db_pool.get_connection()


# Public alias for initialization
init_db_pool = _init_db_pool


@contextmanager
def with_db_cursor(dictionary: bool = True):
    """Context manager for database cursor with automatic commit/rollback.

    Args:
        dictionary: If True, return results as dictionaries.

    Yields:
        Database cursor.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        db_logger.error(f"Database error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def init_database() -> None:
    """Create all database tables and default admin user."""
    create_tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            filename VARCHAR(500) NOT NULL,
            filepath VARCHAR(1000) NOT NULL,
            filesize BIGINT DEFAULT 0,
            duration DECIMAL(10,2) DEFAULT 0,
            width INT DEFAULT 0,
            height INT DEFAULT 0,
            codec VARCHAR(50) DEFAULT '',
            bitrate INT DEFAULT 0,
            framerate DECIMAL(5,2) DEFAULT 0,
            size_bytes BIGINT DEFAULT 0,
            watched_duration DECIMAL(10,2) DEFAULT 0,
            favorite BOOLEAN DEFAULT FALSE,
            last_watched TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            color VARCHAR(7) DEFAULT '#6B7280'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS video_tags (
            video_id INT NOT NULL,
            tag_id INT NOT NULL,
            PRIMARY KEY (video_id, tag_id),
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS collection_videos (
            collection_id INT NOT NULL,
            video_id INT NOT NULL,
            position INT DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (collection_id, video_id),
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS share_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            token VARCHAR(64) UNIQUE NOT NULL,
            video_id INT,
            collection_id INT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
        )
        """,
    ]

    with with_db_cursor() as cursor:
        for table_sql in create_tables:
            cursor.execute(table_sql)
        db_logger.info("Database tables created/verified")

    # Create default admin user if not exists
    try:
        import bcrypt
        admin_password = bcrypt.hashpw(
            "admin123".encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        with with_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT IGNORE INTO users (username, password_hash)
                VALUES ('admin', %s)
                """,
                (admin_password,),
            )
        db_logger.info("Default admin user created/verified")
    except Exception as e:
        db_logger.error(f"Failed to create default admin user: {e}")


def get_dashboard_stats() -> Dict[str, Any]:
    """Get dashboard statistics in a single optimized query.

    Returns:
        Dictionary with total_videos, total_duration, total_size, watched_duration,
        favorites, tag_stats, codec_stats, and res_stats.
    """
    stats: Dict[str, Any] = {
        "total_videos": 0,
        "total_duration": 0.0,
        "total_size": 0,
        "watched_duration": 0.0,
        "favorites": 0,
        "tag_stats": [],
        "codec_stats": [],
        "res_stats": {"uhd": 0, "fhd": 0, "hd": 0, "sd": 0},
    }

    try:
        with with_db_cursor() as cursor:
            # Main stats query
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_videos,
                    COALESCE(SUM(duration), 0) as total_duration,
                    COALESCE(SUM(file_size), 0) as total_size,
                    COALESCE(SUM(progress), 0) as watched_duration,
                    COALESCE(SUM(CASE WHEN is_favorite = TRUE THEN 1 ELSE 0 END), 0) as favorites
                FROM videos
                """
            )
            row = cursor.fetchone()
            if row:
                stats["total_videos"] = int(row["total_videos"])
                stats["total_duration"] = float(row["total_duration"])
                stats["total_size"] = int(row["total_size"])
                stats["watched_duration"] = float(row["watched_duration"])
                stats["favorites"] = int(row["favorites"])

            # Tag stats (top 20)
            cursor.execute(
                """
                SELECT t.name, t.color, COUNT(vt.video_id) as count
                FROM tags t
                LEFT JOIN video_tags vt ON t.id = vt.tag_id
                GROUP BY t.id, t.name, t.color
                ORDER BY count DESC
                LIMIT 20
                """
            )
            stats["tag_stats"] = [
                {"name": r["name"], "color": r["color"], "count": int(r["count"])}
                for r in cursor.fetchall()
            ]

            # Codec stats
            cursor.execute(
                """
                SELECT codec, COUNT(*) as count
                FROM videos
                WHERE codec IS NOT NULL AND codec != ''
                GROUP BY codec
                ORDER BY count DESC
                """
            )
            stats["codec_stats"] = [
                {"codec": r["codec"], "count": int(r["count"])}
                for r in cursor.fetchall()
            ]

            # Resolution stats
            cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN width >= 3840 THEN 1 ELSE 0 END) as uhd,
                    SUM(CASE WHEN width >= 1920 AND width < 3840 THEN 1 ELSE 0 END) as fhd,
                    SUM(CASE WHEN width >= 1280 AND width < 1920 THEN 1 ELSE 0 END) as hd,
                    SUM(CASE WHEN width < 1280 THEN 1 ELSE 0 END) as sd
                FROM videos
                """
            )
            res_row = cursor.fetchone()
            if res_row:
                stats["res_stats"] = {
                    "uhd": int(res_row["uhd"] or 0),
                    "fhd": int(res_row["fhd"] or 0),
                    "hd": int(res_row["hd"] or 0),
                    "sd": int(res_row["sd"] or 0),
                }

    except Exception as e:
        db_logger.error(f"Failed to get dashboard stats: {e}")

    return stats