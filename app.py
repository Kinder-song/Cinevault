from flask import Flask, render_template, request, redirect, session, jsonify, send_file, Response
from functools import wraps
import os
import mysql.connector
import bcrypt
import subprocess
import json
import random
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure directories exist
os.makedirs('thumbnails', exist_ok=True)
os.makedirs('sessions', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)

# Video extensions
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v'}

# ==================== Database ====================

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        return conn
    except mysql.connector.Error:
        return None

def init_database():
    """Initialize database tables and default admin user"""
    # Connect without database first to create it
    init_config = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD
    }
    conn = mysql.connector.connect(**init_config)
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME}")
    cursor.execute(f"USE {Config.DB_NAME}")

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            video_path VARCHAR(500) DEFAULT './video'
        )
    """)

    # Add video_path column if not exists (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN video_path VARCHAR(500) DEFAULT './video' AFTER password_hash")
    except:
        pass  # Column might already exist

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

    # Create default admin
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        pw_hash = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES ('admin', %s)", (pw_hash,))
        print("Created admin/admin123")

    conn.commit()
    cursor.close()
    conn.close()
    return True

# ==================== Auth ====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ==================== Video Utils ====================

def get_video_duration(filepath):
    """Get video duration in seconds by parsing ffmpeg stderr output"""
    cmd = [Config.FFMPEG_PATH, '-i', filepath]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        for line in result.stderr.split('\n'):
            if 'Duration:' in line:
                # Parse "Duration: HH:MM:SS.ms"
                duration_str = line.split('Duration:')[1].split(',')[0].strip()
                parts = duration_str.split(':')
                if len(parts) == 3:
                    h, m, s = parts
                    return int(float(h) * 3600 + float(m) * 60 + float(s))
    except Exception as e:
        print(f"Duration error: {e}")
    return None

def format_duration(seconds):
    """Format seconds to MM:SS or HH:MM:SS"""
    if not seconds:
        return None
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def get_video_info(filepath):
    """Get video metadata by parsing ffmpeg stderr output"""
    cmd = [Config.FFMPEG_PATH, '-i', filepath]
    info = {}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        for line in result.stderr.split('\n'):
            if 'Stream #0' in line and 'Video:' in line:
                # Parse "Stream #0:0(...): Video: h264 ... 3840x2160 [...], ... 60 fps"
                # Extract resolution - look for WxH before [SAR
                import re
                res_match = re.search(r'(\d{2,4})x(\d{2,4})\s+\[SAR', line)
                if res_match:
                    info['width'] = res_match.group(1)
                    info['height'] = res_match.group(2)
                else:
                    # Fallback: try simple WxH pattern
                    res_match = re.search(r'(\d{3,4})x(\d{3,4})', line)
                    if res_match:
                        info['width'] = res_match.group(1)
                        info['height'] = res_match.group(2)
                # Extract fps
                fps_match = re.search(r'(\d+)\s*fps', line)
                if fps_match:
                    info['r_frame_rate'] = fps_match.group(1)
                # Extract bitrate from main line
                bitrate_match = re.search(r'bitrate:\s*(\d+)\s*kb/s', result.stderr)
                if bitrate_match:
                    info['bit_rate'] = str(int(bitrate_match.group(1)) * 1000)
        return info
    except Exception as e:
        print(f"Video info error: {e}")
        return {}

def format_bitrate(bitrate):
    """Format bitrate to human readable"""
    if not bitrate:
        return None
    try:
        bps = int(bitrate)
        return f"{bps / 1000:.0f} kbps"
    except:
        return None

def format_fps(fps_str):
    """Format frame rate to decimal"""
    if not fps_str:
        return None
    try:
        if '/' in fps_str:
            num, den = fps_str.split('/')
            return f"{float(num) / float(den):.2f}"
        return fps_str
    except:
        return None

def format_filesize(size):
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

def generate_thumbnail(filename, video_path=None):
    """Generate thumbnail for video, returns thumbnail path or None"""
    if video_path is None:
        video_path = get_user_video_path(session.get('user_id', ''))
    video_path_full = os.path.join(video_path, filename)
    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)

    if os.path.exists(thumb_path):
        return thumb_path

    duration = get_video_duration(video_path_full)
    if not duration:
        print(f"Could not get duration for {video_path_full}")
        return None

    # Random time point between 0.5s and 10% of video duration
    max_time = min(10, duration * 0.1)
    random_time = random.uniform(0.5, max(1, max_time))

    cmd = [
        Config.FFMPEG_PATH, '-y',
        '-ss', str(random_time),
        '-i', video_path_full,
        '-vframes', '1',
        '-q:v', '2',
        thumb_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.stderr:
            print(f"Thumbnail stderr: {result.stderr}")
        if os.path.exists(thumb_path):
            return thumb_path
    except Exception as e:
        print(f"Thumbnail error: {e}")
    return None

def get_user_video_path(username):
    """Get user's custom video path"""
    conn = get_db_connection()
    if not conn:
        return Config.VIDEO_PATH
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT video_path FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user and user['video_path']:
        return user['video_path']
    return Config.VIDEO_PATH

def scan_videos(video_path=None):
    """Scan video directory and return list of video info"""
    if video_path is None:
        video_path = get_user_video_path(session.get('user_id', ''))
    if not os.path.exists(video_path):
        return []
    videos = []
    for fname in os.listdir(video_path):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in VIDEO_EXTENSIONS:
            continue
        fpath = os.path.join(video_path, fname)
        stat = os.stat(fpath)
        size = stat.st_size
        mtime = stat.st_mtime
        duration = get_video_duration(fpath)
        video_info = get_video_info(fpath)
        videos.append({
            'filename': fname,
            'title': os.path.splitext(fname)[0],
            'size': size,
            'size_formatted': format_filesize(size),
            'duration': duration,
            'duration_formatted': format_duration(duration),
            'created': mtime,
            'width': video_info.get('width', ''),
            'height': video_info.get('height', ''),
            'bitrate': format_bitrate(video_info.get('bit_rate', '')),
            'fps': format_fps(video_info.get('r_frame_rate', ''))
        })
    return videos

# ==================== Routes ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        session['user_id'] = username
        session['username'] = username
        session['video_path'] = user.get('video_path', Config.VIDEO_PATH)
        return jsonify({'success': True})

    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
@login_required
def index():
    videos = scan_videos()

    # Get tags from DB
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.name, t.color, v.filename FROM tags t
        JOIN video_tags vt ON t.id = vt.tag_id
        JOIN videos v ON v.id = vt.video_id
    """)
    tags_data = cursor.fetchall()
    cursor.close()
    conn.close()

    # Group tags by video filename
    tags_by_video = {}
    for tag in tags_data:
        fname = tag['filename']
        if fname not in tags_by_video:
            tags_by_video[fname] = []
        tags_by_video[fname].append({'name': tag['name'], 'color': tag['color']})

    # Ensure thumbnails exist
    for v in videos:
        v['thumbnail'] = generate_thumbnail(v['filename'])

    return render_template('index.html', videos=videos, tags_by_video=tags_by_video)

@app.route('/video/<filename>')
@login_required
def video_page(filename):
    video_path = get_user_video_path(session['user_id'])
    video_path_full = os.path.join(video_path, filename)
    if not os.path.exists(video_path_full):
        return "Video not found", 404

    size = os.stat(video_path_full).st_size
    video_info = get_video_info(video_path_full)

    width = video_info.get('width', '')
    height = video_info.get('height', '')
    bitrate = format_bitrate(video_info.get('bit_rate', ''))
    fps = format_fps(video_info.get('r_frame_rate', ''))

    video = {
        'filename': filename,
        'title': os.path.splitext(filename)[0],
        'size': size,
        'size_formatted': format_filesize(size),
        'duration': None,
        'duration_formatted': None,
        'width': width,
        'height': height,
        'bitrate': bitrate,
        'fps': fps
    }

    # Get tags
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.name, t.color FROM tags t
        JOIN video_tags vt ON t.id = vt.tag_id
        JOIN videos v ON v.id = vt.video_id
        WHERE v.filename = %s
    """, (filename,))
    tags = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('video.html', video=video, tags=tags)

@app.route('/stream/<filename>')
@login_required
def stream_video(filename):
    """Stream video with Range request support"""
    video_path = get_user_video_path(session['user_id'])
    video_path_full = os.path.join(video_path, filename)
    if not os.path.exists(video_path_full):
        return "Video not found", 404

    file_size = os.stat(video_path_full).st_size

    range_header = request.headers.get('Range')
    if range_header:
        range_match = range_header.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        length = end - start + 1

        def generate():
            with open(video_path_full, 'rb') as f:
                f.seek(start)
                remaining = length
                chunk_size = 1024 * 1024  # 1MB chunks
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        resp = Response(generate(), status=206)
        resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Content-Length'] = length
        resp.headers['Content-Type'] = 'video/mp4'
        return resp

    # No Range header - stream entire file
    def generate():
        with open(video_path_full, 'rb') as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    resp = Response(generate(), status=200)
    resp.headers['Content-Length'] = file_size
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Content-Type'] = 'video/mp4'
    return resp

@app.route('/thumbnail/<filename>')
@login_required
def thumbnail(filename):
    """Return thumbnail image for video"""
    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)

    if not os.path.exists(thumb_path):
        generate_thumbnail(filename)

    if os.path.exists(thumb_path):
        return send_file(thumb_path, mimetype='image/jpeg')

    return Response(status=404)

@app.route('/api/videos')
@login_required
def api_videos():
    """Get all videos with tags"""
    videos = scan_videos()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.name, t.color, v.filename FROM tags t
        JOIN video_tags vt ON t.id = vt.tag_id
        JOIN videos v ON v.id = vt.video_id
    """)
    tags_data = cursor.fetchall()
    cursor.close()
    conn.close()

    tags_by_video = {}
    for tag in tags_data:
        fname = tag['filename']
        if fname not in tags_by_video:
            tags_by_video[fname] = []
        tags_by_video[fname].append({'name': tag['name'], 'color': tag['color']})

    return jsonify({'videos': videos, 'tags': tags_by_video})

@app.route('/api/video/<filename>/tags', methods=['POST'])
@login_required
def add_tag(filename):
    """Add tag to video"""
    data = request.get_json()
    tag_name = data.get('tag', '').strip()

    if not tag_name:
        return jsonify({'error': 'Tag name required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get or create video
    cursor.execute("SELECT id FROM videos WHERE filename = %s", (filename,))
    video = cursor.fetchone()
    if not video:
        cursor.execute("INSERT INTO videos (filename, title) VALUES (%s, %s)",
                     (filename, os.path.splitext(filename)[0]))
        video_id = cursor.lastrowid
    else:
        video_id = video['id']

    # Get or create tag
    cursor.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
    tag = cursor.fetchone()
    if not tag:
        cursor.execute("INSERT INTO tags (name) VALUES (%s)", (tag_name,))
        tag_id = cursor.lastrowid
    else:
        tag_id = tag['id']

    # Link
    try:
        cursor.execute("INSERT INTO video_tags (video_id, tag_id) VALUES (%s, %s)",
                      (video_id, tag_id))
        conn.commit()
        success = True
    except mysql.connector.IntegrityError:
        success = True  # Already linked

    cursor.close()
    conn.close()
    return jsonify({'success': success})

@app.route('/api/video/<filename>/tags/<tag_name>', methods=['DELETE'])
@login_required
def delete_tag(filename, tag_name):
    """Delete tag from video"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        DELETE vt FROM video_tags vt
        JOIN videos v ON v.id = vt.video_id
        JOIN tags t ON t.id = vt.tag_id
        WHERE v.filename = %s AND t.name = %s
    """, (filename, tag_name))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/video/<filename>/refresh-thumb', methods=['POST'])
@login_required
def refresh_thumbnail(filename):
    """Refresh video thumbnail"""
    video_path = get_user_video_path(session['user_id'])
    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)

    # Remove existing
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    thumb = generate_thumbnail(filename, video_path)
    return jsonify({'success': bool(thumb), 'thumbnail': thumb})

@app.route('/api/video/<filename>/info', methods=['GET'])
@login_required
def get_video_info_api(filename):
    """Get video metadata API"""
    video_path = get_user_video_path(session['user_id'])
    video_path_full = os.path.join(video_path, filename)

    if not os.path.exists(video_path_full):
        return jsonify({'error': 'Video not found'}), 404

    video_info = get_video_info(video_path_full)
    size = os.stat(video_path_full).st_size

    return jsonify({
        'filename': filename,
        'size': format_filesize(size),
        'width': video_info.get('width', ''),
        'height': video_info.get('height', ''),
        'bitrate': format_bitrate(video_info.get('bit_rate', '')),
        'fps': format_fps(video_info.get('r_frame_rate', ''))
    })

@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    """Get current user profile"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, video_path FROM users WHERE username = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(user)

@app.route('/api/user/profile', methods=['POST'])
@login_required
def update_user_profile():
    """Update user profile (username, password, video_path)"""
    data = request.get_json()
    username = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    updates = []
    params = []

    # Update username
    new_username = data.get('username', '').strip()
    if new_username and new_username != username:
        # Check if username exists
        cursor.execute("SELECT id FROM users WHERE username = %s AND username != %s", (new_username, username))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Username already exists'}), 400
        updates.append("username = %s")
        params.append(new_username)
        session['user_id'] = new_username
        session['username'] = new_username

    # Update password (requires current password verification)
    new_password = data.get('password', '').strip()
    verify_password = data.get('verify_password', '').strip()
    if new_password:
        if not verify_password:
            return jsonify({'error': 'Current password required'}), 400
        # Verify current password
        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not bcrypt.checkpw(verify_password.encode(), user['password_hash'].encode()):
            return jsonify({'error': 'Current password incorrect'}), 400
        pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        updates.append("password_hash = %s")
        params.append(pw_hash)

    # Update video path
    video_path = data.get('video_path', '').strip()
    if video_path:
        updates.append("video_path = %s")
        params.append(video_path)
        session['video_path'] = video_path

    if updates:
        params.append(username)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE username = %s", params)
        conn.commit()

    cursor.close()
    conn.close()
    return jsonify({'success': True})

@app.route('/settings')
@login_required
def settings_page():
    """Settings page"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, video_path FROM users WHERE username = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('settings.html', user=user)

# ==================== Init ====================

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=55300, debug=True)