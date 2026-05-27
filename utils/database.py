import mysql.connector
from mysql.connector import Error
import bcrypt

DB_CONFIG = {
    'host': '43.143.143.187',
    'port': 3306,
    'user': 'root',
    'password': 'nugtar-keZzi8-ryqcym',
    'database': 'video'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables and default admin user"""
    # First connect without database to create it
    init_config = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    conn = mysql.connector.connect(**init_config)
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cursor.execute(f"USE {DB_CONFIG['database']}")

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        )
    """)

    # Create videos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(500) UNIQUE NOT NULL,
            title VARCHAR(500),
            duration INT,
            size BIGINT,
            thumbnail_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create tags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            color VARCHAR(20) DEFAULT '#7b9cff'
        )
    """)

    # Create video_tags junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_tags (
            video_id INT,
            tag_id INT,
            PRIMARY KEY (video_id, tag_id)
        )
    """)

    # Create default admin if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", ('admin', password_hash))
        print("Default admin user created (admin/admin123)")

    conn.commit()
    cursor.close()
    conn.close()
    return True

def verify_user(username, password):
    """Verify username and password, returns True if valid"""
    conn = get_db_connection()
    if not conn:
        return False

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return True
    return False