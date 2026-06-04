"""Database service for CineVault with MySQL connection pooling."""

from contextlib import contextmanager
from typing import Any, Optional

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
    """Create all database tables and default admin user.

    NOTE: The schema below mirrors the live production database. Keep CREATE TABLE
    in sync with the column names the rest of the codebase uses:
      - videos.favorite, videos.watched_duration (NOT is_favorite / progress)
      - share_tokens.video_filename (NOT video_id)
    """
    create_tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            video_path VARCHAR(1000) DEFAULT NULL,
            password_changed BOOLEAN DEFAULT FALSE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(500) NOT NULL,
            title VARCHAR(255) NOT NULL,
            duration DECIMAL(10,2) DEFAULT 0,
            audio_sample_rate INT DEFAULT 0,
            audio_channels INT DEFAULT 0,
            audio_codec VARCHAR(50) DEFAULT '',
            favorite TINYINT(1) DEFAULT 0,
            rating INT DEFAULT 0,
            watched_duration INT DEFAULT 0,
            codec VARCHAR(50) DEFAULT '',
            bitrate INT DEFAULT 0,
            fps DECIMAL(5,2) DEFAULT 0,
            height INT DEFAULT 0,
            width INT DEFAULT 0,
            file_mtime BIGINT DEFAULT 0,
            file_size BIGINT DEFAULT 0,
            size BIGINT DEFAULT 0,
            thumbnail_path VARCHAR(500) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            video_filename VARCHAR(500) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            video_id INT NOT NULL,
            user_id INT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_comments_video (video_id),
            INDEX idx_comments_user (user_id),
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS watch_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            video_id INT NOT NULL,
            watched_seconds INT DEFAULT 0,
            watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_history_user_time (user_id, watched_at),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
        )
        """,
    ]

    with with_db_cursor() as cursor:
        for table_sql in create_tables:
            cursor.execute(table_sql)
        db_logger.info("Database tables created/verified")

        # Add password_changed column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN password_changed BOOLEAN DEFAULT FALSE")
            db_logger.info("Added password_changed column to users table")
        except Exception as e:
            if 'Duplicate column' in str(e) or 'Unknown column' not in str(e):
                db_logger.debug(f"password_changed column already exists or migration skipped: {e}")
            else:
                db_logger.warning(f"Could not add password_changed column: {e}")

        # Add users.video_path column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN video_path VARCHAR(1000) DEFAULT NULL")
            db_logger.info("Added video_path column to users table")
        except Exception as e:
            if 'Duplicate column' in str(e):
                db_logger.debug(f"video_path column already exists: {e}")
            else:
                db_logger.warning(f"Could not add video_path column: {e}")

        # NOTE: MySQL 8.0 does NOT support `CREATE INDEX IF NOT EXISTS`.
        # Use information_schema check + try/except to be safe.
        def ensure_index(cur, idx_name, table, cols):
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = %s AND index_name = %s",
                (table, idx_name),
            )
            if cur.fetchone()[0] == 0:
                cur.execute(f"CREATE INDEX {idx_name} ON {table}({cols})")
                db_logger.info(f"Created index {idx_name} on {table}({cols})")
            else:
                db_logger.debug(f"Index {idx_name} already exists on {table}")

        indexes = [
            ("idx_videos_filename", "videos", "filename"),
            ("idx_videos_created", "videos", "created_at"),
            ("idx_video_tags_video", "video_tags", "video_id"),
            ("idx_video_tags_tag", "video_tags", "tag_id"),
            ("idx_collection_videos_collection", "collection_videos", "collection_id"),
        ]
        for idx_name, table, cols in indexes:
            try:
                ensure_index(cursor, idx_name, table, cols)
            except Exception as e:
                db_logger.warning(f"Index {idx_name} creation skipped: {e}")
        db_logger.info("Database indexes created/verified")

    # Create default admin user if not exists
    # Default password: admin123 (bcrypt hashed)
    # User must change password on first login
    try:
        import bcrypt

        # Default admin password
        admin_password = 'admin123'
        admin_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        with with_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT IGNORE INTO users (username, password_hash, password_changed)
                VALUES ('admin', %s, FALSE)
                """,
                (admin_hash,),
            )
            # Log the default password (first time only, when user is created)
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if cursor.fetchone():
                db_logger.info(f"Default admin user created. Default password: {admin_password} (change on first login)")
        db_logger.info("Default admin user created/verified")
    except Exception as e:
        db_logger.error(f"Failed to create default admin user: {e}")