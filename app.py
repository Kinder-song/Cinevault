from flask import Flask, render_template, request, redirect, session, jsonify, send_file, Response, send_from_directory
from functools import wraps
from contextlib import contextmanager
import os
import re
import mysql.connector
from mysql.connector import pooling
import bcrypt
import subprocess
import json
import random
import secrets
import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

for d in ['thumbnails', 'sessions', 'static/css', 'static/js', 'cache']:
    os.makedirs(d, exist_ok=True)

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v'}
VIDEO_MIME_TYPES = {
    '.mp4': 'video/mp4', '.mkv': 'video/x-matroska', '.webm': 'video/webm',
    '.mov': 'video/quicktime', '.avi': 'video/x-msvideo', '.m4v': 'video/x-m4v',
}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass'}

# ==================== Database ====================

db_pool = None

def _init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = pooling.MySQLConnectionPool(
                pool_name="cinevault_pool", pool_size=8, pool_reset_session=True,
                host=Config.DB_HOST, port=Config.DB_PORT,
                user=Config.DB_USER, password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
        except Exception:
            return None
    return db_pool

def get_db_connection():
    pool = _init_db_pool()
    if pool is None:
        return None
    try:
        return pool.get_connection()
    except Exception:
        return None

@contextmanager
def with_db_cursor(dictionary=True):
    """Context manager for database operations with automatic cleanup."""
    conn = get_db_connection()
    if conn is None:
        yield None
        return
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def init_database():
    init_config = {'host': Config.DB_HOST, 'port': Config.DB_PORT,
                   'user': Config.DB_USER, 'password': Config.DB_PASSWORD}
    conn = mysql.connector.connect(**init_config)
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME}")
    cursor.execute(f"USE {Config.DB_NAME}")

    # Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            video_path VARCHAR(500) DEFAULT './video'
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN video_path VARCHAR(500) DEFAULT './video' AFTER password_hash")
    except: pass

    # Videos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(500) UNIQUE NOT NULL,
            title VARCHAR(500),
            duration INT, file_size BIGINT DEFAULT 0, file_mtime INT DEFAULT 0,
            width INT DEFAULT 0, height INT DEFAULT 0,
            fps VARCHAR(20) DEFAULT '', bitrate VARCHAR(20) DEFAULT '',
            codec VARCHAR(50) DEFAULT '', audio_codec VARCHAR(50) DEFAULT '',
            audio_channels INT DEFAULT 0, audio_sample_rate INT DEFAULT 0,
            thumbnail_path VARCHAR(500) DEFAULT '',
            progress INT DEFAULT 0, rating INT DEFAULT 0, is_favorite TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_filename (filename), INDEX idx_file_mtime (file_mtime),
            INDEX idx_is_favorite (is_favorite)
        )
    """)

    for col, col_def in [
        ('file_size', 'BIGINT DEFAULT 0'), ('file_mtime', 'INT DEFAULT 0'),
        ('width', 'INT DEFAULT 0'), ('height', 'INT DEFAULT 0'),
        ('fps', "VARCHAR(20) DEFAULT ''"), ('bitrate', "VARCHAR(20) DEFAULT ''"),
        ('codec', "VARCHAR(50) DEFAULT ''"), ('thumbnail_path', "VARCHAR(500) DEFAULT ''"),
        ('progress', 'INT DEFAULT 0'), ('rating', 'INT DEFAULT 0'),
        ('is_favorite', 'TINYINT DEFAULT 0'),
        ('audio_codec', "VARCHAR(50) DEFAULT ''"), ('audio_channels', 'INT DEFAULT 0'),
        ('audio_sample_rate', 'INT DEFAULT 0'),
    ]:
        try:
            cursor.execute(f"ALTER TABLE videos ADD COLUMN {col} {col_def} AFTER duration")
        except: pass

    # Tags
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL,
            color VARCHAR(20) DEFAULT '#7b9cff'
        )
    """)

    # Video_tags
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_tags (
            video_id INT, tag_id INT, PRIMARY KEY (video_id, tag_id)
        )
    """)

    # Collections
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(200) NOT NULL,
            description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_videos (
            collection_id INT, video_id INT, position INT DEFAULT 0,
            PRIMARY KEY (collection_id, video_id)
        )
    """)

    # Share tokens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS share_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY, token VARCHAR(64) UNIQUE NOT NULL,
            video_filename VARCHAR(500) NOT NULL, expires_at DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Default admin
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

# ==================== Metadata Extraction ====================

def _extract_metadata_ffmpeg(filepath):
    cmd = [Config.FFMPEG_PATH, '-i', filepath]
    meta = {'duration': None, 'width': 0, 'height': 0, 'fps': '', 'bitrate': '',
            'codec': '', 'audio_codec': '', 'audio_channels': 0, 'audio_sample_rate': 0}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        stderr = result.stderr

        for line in stderr.split('\n'):
            if 'Duration:' in line:
                d = line.split('Duration:')[1].split(',')[0].strip()
                parts = d.split(':')
                if len(parts) == 3:
                    meta['duration'] = int(float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2]))
                break

        for line in stderr.split('\n'):
            if 'Stream #0' in line and 'Video:' in line:
                cm = re.search(r'Video:\s*(\S+)', line)
                if cm: meta['codec'] = cm.group(1)
                rm = re.search(r'(\d{2,4})x(\d{2,4})\s+\[SAR', line)
                if not rm: rm = re.search(r'(\d{3,4})x(\d{3,4})', line)
                if rm: meta['width'] = int(rm.group(1)); meta['height'] = int(rm.group(2))
                fm = re.search(r'(\d+(?:\.\d+)?)\s*fps', line)
                if fm: meta['fps'] = fm.group(1)

            if 'Stream #0' in line and 'Audio:' in line:
                acm = re.search(r'Audio:\s*(\S+)', line)
                if acm: meta['audio_codec'] = acm.group(1)
                chm = re.search(r'stereo|mono|(\d+)\s*channels', line, re.I) or re.search(r',\s*(\d+)\s*ch', line)
                if chm:
                    try: meta['audio_channels'] = int(chm.group(1)) if chm.group(1).isdigit() else (2 if 'stereo' in chm.group(0).lower() else 1)
                    except: pass
                srm = re.search(r'(\d+)\s*Hz', line)
                if srm: meta['audio_sample_rate'] = int(srm.group(1))

        bm = re.search(r'bitrate:\s*(\d+)\s*kb/s', stderr)
        if bm: meta['bitrate'] = str(int(bm.group(1)) * 1000)
    except Exception as e:
        print(f"ffmpeg error: {e}")
    return meta

# ==================== Thumbnail ====================

def _generate_thumbnail(filename, video_path_full):
    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        probe_cmd = [Config.FFMPEG_PATH, '-v', 'quiet', '-show_entries', 'format=duration',
                     '-of', 'csv=p=0', video_path_full]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=8)
        duration = float(result.stdout.strip()) if result.stdout.strip() else None
    except:
        duration = None
    if not duration or duration <= 0:
        return None
    seek_time = random.uniform(0.5, min(10, duration * 0.1))
    cmd = [Config.FFMPEG_PATH, '-y', '-ss', str(seek_time), '-i', video_path_full,
           '-vframes', '1', '-q:v', '2', thumb_path]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if os.path.exists(thumb_path):
            return thumb_path
    except Exception as e:
        print(f"Thumbnail error: {e}")
    return None

# ==================== DB Sync ====================

def _sync_video_to_db(filename, video_path_full):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        stat = os.stat(video_path_full)
        file_size, file_mtime = stat.st_size, int(stat.st_mtime)
    except OSError:
        cursor.close(); conn.close(); return None

    cursor.execute("SELECT * FROM videos WHERE filename = %s", (filename,))
    row = cursor.fetchone()
    needs = not row or row.get('file_mtime', 0) != file_mtime or row.get('file_size', 0) != file_size

    if needs:
        meta = _extract_metadata_ffmpeg(video_path_full)
        thumb = _generate_thumbnail(filename, video_path_full)
        if row:
            cursor.execute("""UPDATE videos SET file_size=%s,file_mtime=%s,duration=%s,
                width=%s,height=%s,fps=%s,bitrate=%s,codec=%s,audio_codec=%s,
                audio_channels=%s,audio_sample_rate=%s,thumbnail_path=%s
                WHERE filename=%s""",
                (file_size, file_mtime, meta['duration'], meta['width'], meta['height'],
                 meta['fps'], meta['bitrate'], meta['codec'], meta['audio_codec'],
                 meta['audio_channels'], meta['audio_sample_rate'], thumb or '', filename))
        else:
            cursor.execute("""INSERT INTO videos (filename,title,file_size,file_mtime,duration,
                width,height,fps,bitrate,codec,audio_codec,audio_channels,audio_sample_rate,thumbnail_path)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (filename, os.path.splitext(filename)[0], file_size, file_mtime,
                 meta['duration'], meta['width'], meta['height'], meta['fps'], meta['bitrate'],
                 meta['codec'], meta['audio_codec'], meta['audio_channels'],
                 meta['audio_sample_rate'], thumb or ''))
        conn.commit()
        cursor.execute("SELECT * FROM videos WHERE filename = %s", (filename,))
        row = cursor.fetchone()
    cursor.close(); conn.close()
    return row

def _get_all_videos_from_db():
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM videos ORDER BY filename")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def _sync_and_get_videos(video_path):
    if not os.path.exists(video_path):
        return _get_all_videos_from_db()
    files_on_disk = {}
    for fname in os.listdir(video_path):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in VIDEO_EXTENSIONS: continue
        try:
            st = os.stat(os.path.join(video_path, fname))
            files_on_disk[fname] = (st.st_size, int(st.st_mtime))
        except OSError: continue
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT filename, file_size, file_mtime FROM videos")
    existing = {r['filename']: (r['file_size'] or 0, r['file_mtime'] or 0) for r in cursor.fetchall()}
    cursor.close(); conn.close()
    for fname, (size, mtime) in files_on_disk.items():
        prev = existing.get(fname)
        if not prev or prev[0] != size or prev[1] != mtime:
            _sync_video_to_db(fname, os.path.join(video_path, fname))
    return _get_all_videos_from_db()

def _db_row_to_video_dict(row):
    return {
        'filename': row['filename'],
        'title': row.get('title') or os.path.splitext(row['filename'])[0],
        'size': row.get('file_size', 0),
        'size_formatted': format_filesize(row.get('file_size', 0)),
        'duration': row.get('duration'),
        'duration_formatted': format_duration(row.get('duration')),
        'created': row.get('file_mtime', 0),
        'width': str(row.get('width', '')) if row.get('width') else '',
        'height': str(row.get('height', '')) if row.get('height') else '',
        'bitrate': format_bitrate(row.get('bitrate', '')),
        'fps': format_fps(row.get('fps', '')),
        'codec': row.get('codec', ''),
        'audio_codec': row.get('audio_codec', ''),
        'audio_channels': row.get('audio_channels', 0),
        'audio_sample_rate': row.get('audio_sample_rate', 0),
        'thumbnail': row.get('thumbnail_path', ''),
        'progress': row.get('progress', 0),
        'rating': row.get('rating', 0),
        'is_favorite': bool(row.get('is_favorite', 0)),
    }

# ==================== Format Utilities ====================

def format_duration(seconds):
    if not seconds: return None
    h, m = divmod(int(seconds), 3600)
    m, s = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def format_bitrate(bitrate):
    if not bitrate: return None
    try: return f"{int(bitrate) / 1000:.0f} kbps"
    except: return None

def format_fps(fps_str):
    if not fps_str: return None
    try:
        if '/' in fps_str:
            n, d = fps_str.split('/')
            return f"{float(n)/float(d):.2f}"
        return fps_str
    except: return None

def format_filesize(size):
    s = float(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if s < 1024: return f"{s:.1f} {unit}"
        s /= 1024
    return f"{s:.1f} TB"

def get_user_video_path(username):
    # Try session cache first
    if 'video_path' in session:
        return session['video_path']
    with with_db_cursor() as cursor:
        if cursor is None:
            return Config.VIDEO_PATH
        cursor.execute("SELECT video_path FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        path = user['video_path'] if (user and user['video_path']) else Config.VIDEO_PATH
        session['video_path'] = path
        return path

# ==================== Routes: Auth ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        session['user_id'] = username
        session['username'] = username
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==================== Routes: Index (paginated) ====================

@app.route('/')
@login_required
def index():
    video_path = get_user_video_path(session['user_id'])
    db_rows = _sync_and_get_videos(video_path)
    all_videos = [_db_row_to_video_dict(r) for r in db_rows]

    # Server-side pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    per_page = min(max(per_page, 12), 96)  # clamp 12-96
    total = len(all_videos)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(page, 1), total_pages)
    start = (page - 1) * per_page
    videos = all_videos[start:start + per_page]

    # Tags
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""SELECT t.name, t.color, v.filename FROM tags t
        JOIN video_tags vt ON t.id=vt.tag_id JOIN videos v ON v.id=vt.video_id""")
    tags_data = cursor.fetchall()
    cursor.close(); conn.close()
    tags_by_video = {}
    for tag in tags_data:
        tags_by_video.setdefault(tag['filename'], []).append({'name': tag['name'], 'color': tag['color']})

    # Collections for filter
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM collections ORDER BY name")
    collections = cursor.fetchall()
    cursor.close(); conn.close()

    return render_template('index.html', videos=videos, tags_by_video=tags_by_video,
                           page=page, total_pages=total_pages, per_page=per_page,
                           total=total, collections=collections)

# ==================== Routes: Video Page ====================

@app.route('/video/<filename>')
@login_required
def video_page(filename):
    video_path = get_user_video_path(session['user_id'])
    video_path_full = os.path.join(video_path, filename)
    if not os.path.exists(video_path_full):
        return "Video not found", 404
    row = _sync_video_to_db(filename, video_path_full)
    if not row: return "Video not found", 404
    video = _db_row_to_video_dict(row)

    # Subtitles
    subtitles = _scan_subtitles(filename, video_path)

    # Screenshots
    screenshots = _scan_screenshots(filename, video_path)

    # Tags
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""SELECT t.name, t.color FROM tags t
        JOIN video_tags vt ON t.id=vt.tag_id JOIN videos v ON v.id=vt.video_id
        WHERE v.filename=%s""", (filename,))
    tags = cursor.fetchall()
    cursor.close(); conn.close()

    return render_template('video.html', video=video, tags=tags,
                           subtitles=subtitles, screenshots=screenshots)

# ==================== Routes: Stream ====================

@app.route('/stream/<filename>')
@login_required
def stream_video(filename):
    video_path = get_user_video_path(session['user_id'])
    fp = os.path.join(video_path, filename)
    if not os.path.exists(fp): return "Video not found", 404
    file_size = os.stat(fp).st_size; file_mtime = int(os.stat(fp).st_mtime)
    ext = os.path.splitext(filename)[1].lower()
    ct = VIDEO_MIME_TYPES.get(ext, 'video/mp4')
    BUF = 2 * 1024 * 1024  # 2MB I/O buffer + chunk size

    range_header = request.headers.get('Range')
    if range_header:
        try:
            parts = range_header.replace('bytes=', '').split('-')
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                return "Range Not Satisfiable", 416
        except (ValueError, IndexError):
            return "Bad Range", 400
        length = end - start + 1
        f = open(fp, 'rb', buffering=BUF)
        f.seek(start)
        def gen_range():
            remaining = length
            try:
                while remaining > 0:
                    chunk = f.read(min(BUF, remaining))
                    if not chunk: break
                    remaining -= len(chunk); yield chunk
            finally:
                f.close()
        resp = Response(gen_range(), 206, direct_passthrough=True)
        resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        resp.headers['Content-Length'] = str(length)
    else:
        f = open(fp, 'rb', buffering=BUF)
        def gen_full():
            try:
                while True:
                    chunk = f.read(BUF)
                    if not chunk: break
                    yield chunk
            finally:
                f.close()
        resp = Response(gen_full(), 200, direct_passthrough=True)
        resp.headers['Content-Length'] = str(file_size)

    resp.headers['Content-Type'] = ct
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Cache-Control'] = 'private, max-age=86400'
    resp.headers['ETag'] = f'"{file_mtime}-{file_size}"'
    return resp

# ==================== Routes: Thumbnail & Static ====================

@app.route('/thumbnail/<filename>')
@login_required
def thumbnail(filename):
    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)
    if not os.path.exists(thumb_path):
        vp = get_user_video_path(session['user_id'])
        fp = os.path.join(vp, filename)
        if os.path.exists(fp): _generate_thumbnail(filename, fp)
    if os.path.exists(thumb_path):
        resp = send_file(thumb_path, mimetype='image/jpeg')
        resp.headers['Cache-Control'] = 'public, max-age=604800'
        return resp
    return Response(status=404)

@app.route('/static/<path:filepath>')
def static_with_cache(filepath):
    resp = send_from_directory('static', filepath)
    resp.headers['Cache-Control'] = 'public, max-age=604800, immutable'
    return resp

# ==================== Routes: Subtitle ====================

def _scan_subtitles(filename, video_dir):
    base = os.path.splitext(filename)[0]
    subs = []
    for ext in SUBTITLE_EXTENSIONS:
        sub_path = os.path.join(video_dir, base + ext)
        if os.path.exists(sub_path):
            subs.append({'filename': base + ext, 'ext': ext[1:], 'label': {'srt': 'SubRip', 'vtt': 'WebVTT', 'ass': 'ASS'}.get(ext[1:], ext[1:].upper())})
    return subs

@app.route('/subtitle/<filename>')
@login_required
def serve_subtitle(filename):
    video_path = get_user_video_path(session['user_id'])
    fp = os.path.join(video_path, filename)
    if not os.path.exists(fp):
        return "Not found", 404
    ext = os.path.splitext(filename)[1].lower()
    mt = {'srt': 'text/plain', 'vtt': 'text/vtt', 'ass': 'text/plain'}.get(ext[1:], 'text/plain')
    resp = send_file(fp, mimetype=mt)
    resp.headers['Cache-Control'] = 'public, max-age=604800'
    return resp

# ==================== Routes: Screenshots ====================

def _scan_screenshots(filename, video_dir):
    base = os.path.splitext(filename)[0]
    shots = []
    if not os.path.exists(video_dir):
        return shots
    for fname in sorted(os.listdir(video_dir)):
        if not fname.startswith(base):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext in IMAGE_EXTENSIONS and fname.endswith(ext) and not fname.endswith('.jpg'):
            # Match screenshots like "base_01.png", "base_screenshot.png"
            shots.append({'filename': fname, 'path': f'/screenshot/{fname}'})
    return shots

@app.route('/screenshot/<filename>')
@login_required
def serve_screenshot(filename):
    video_path = get_user_video_path(session['user_id'])
    fp = os.path.join(video_path, filename)
    if not os.path.exists(fp):
        # also check thumbnails dir
        fp = os.path.join('thumbnails', filename)
    if not os.path.exists(fp):
        return "Not found", 404
    return send_file(fp)

# ==================== Routes: API ====================

@app.route('/api/videos')
@login_required
def api_videos():
    video_path = get_user_video_path(session['user_id'])
    db_rows = _sync_and_get_videos(video_path)
    videos = [_db_row_to_video_dict(r) for r in db_rows]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""SELECT t.name, t.color, v.filename FROM tags t
        JOIN video_tags vt ON t.id=vt.tag_id JOIN videos v ON v.id=vt.video_id""")
    tags_data = cursor.fetchall()
    cursor.close(); conn.close()
    tags_by_video = {}
    for tag in tags_data:
        tags_by_video.setdefault(tag['filename'], []).append({'name': tag['name'], 'color': tag['color']})
    return jsonify({'videos': videos, 'tags': tags_by_video})

@app.route('/api/video/<filename>/tags', methods=['POST'])
@login_required
def add_tag(filename):
    data = request.get_json()
    tag_name = data.get('tag', '').strip()
    if not tag_name: return jsonify({'error': 'Tag name required'}), 400
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM videos WHERE filename = %s", (filename,))
    video = cursor.fetchone()
    if not video:
        cursor.execute("INSERT INTO videos (filename, title) VALUES (%s, %s)", (filename, os.path.splitext(filename)[0]))
        video_id = cursor.lastrowid
    else:
        video_id = video['id']
    cursor.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
    tag = cursor.fetchone()
    if not tag:
        cursor.execute("INSERT INTO tags (name) VALUES (%s)", (tag_name,))
        tag_id = cursor.lastrowid
    else:
        tag_id = tag['id']
    try:
        cursor.execute("INSERT INTO video_tags (video_id, tag_id) VALUES (%s, %s)", (video_id, tag_id))
        conn.commit()
    except mysql.connector.IntegrityError: pass
    cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/video/<filename>/tags/<tag_name>', methods=['DELETE'])
@login_required
def delete_tag(filename, tag_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""DELETE vt FROM video_tags vt JOIN videos v ON v.id=vt.video_id
        JOIN tags t ON t.id=vt.tag_id WHERE v.filename=%s AND t.name=%s""", (filename, tag_name))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/video/<filename>/refresh-thumb', methods=['POST'])
@login_required
def refresh_thumbnail(filename):
    video_path = get_user_video_path(session['user_id'])
    fp = os.path.join(video_path, filename)
    thumb_name = f"{os.path.splitext(filename)[0]}.jpg"
    thumb_path = os.path.join('thumbnails', thumb_name)
    if os.path.exists(thumb_path): os.remove(thumb_path)
    new_thumb = _generate_thumbnail(filename, fp)
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE videos SET thumbnail_path=%s WHERE filename=%s", (new_thumb or '', filename))
        conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': bool(new_thumb), 'thumbnail': new_thumb})

@app.route('/api/video/<filename>/info', methods=['GET'])
@login_required
def get_video_info_api(filename):
    video_path = get_user_video_path(session['user_id'])
    fp = os.path.join(video_path, filename)
    if not os.path.exists(fp): return jsonify({'error': 'Not found'}), 404
    row = _sync_video_to_db(filename, fp)
    if not row: return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'filename': filename, 'size': format_filesize(row.get('file_size', 0)),
        'width': str(row.get('width','')) if row.get('width') else '',
        'height': str(row.get('height','')) if row.get('height') else '',
        'bitrate': format_bitrate(row.get('bitrate','')), 'fps': format_fps(row.get('fps','')),
        'codec': row.get('codec',''), 'audio_codec': row.get('audio_codec',''),
        'audio_channels': row.get('audio_channels',0), 'audio_sample_rate': row.get('audio_sample_rate',0),
    })

# ==================== Routes: Progress / Rating / Favorite ====================

@app.route('/api/video/<filename>/progress', methods=['POST'])
@login_required
def save_progress(filename):
    data = request.get_json()
    progress = data.get('progress', 0)
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE videos SET progress=%s WHERE filename=%s", (int(progress), filename))
        conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/video/<filename>/favorite', methods=['POST'])
@login_required
def toggle_favorite(filename):
    data = request.get_json()
    val = 1 if data.get('is_favorite') else 0
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE videos SET is_favorite=%s WHERE filename=%s", (val, filename))
        conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/video/<filename>/rating', methods=['POST'])
@login_required
def set_rating(filename):
    data = request.get_json()
    rating = max(0, min(5, int(data.get('rating', 0))))
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE videos SET rating=%s WHERE filename=%s", (rating, filename))
        conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': True})

# ==================== Routes: Collections ====================

@app.route('/api/collections', methods=['GET'])
@login_required
def list_collections():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""SELECT c.*, COUNT(cv.video_id) as video_count
        FROM collections c LEFT JOIN collection_videos cv ON c.id=cv.collection_id
        GROUP BY c.id ORDER BY c.name""")
    cols = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify({'collections': cols})

@app.route('/api/collections', methods=['POST'])
@login_required
def create_collection():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name: return jsonify({'error': 'Name required'}), 400
    desc = data.get('description', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("INSERT INTO collections (name, description) VALUES (%s, %s)", (name, desc))
    conn.commit()
    col_id = cursor.lastrowid
    cursor.close(); conn.close()
    return jsonify({'success': True, 'id': col_id})

@app.route('/api/collections/<int:col_id>', methods=['DELETE'])
@login_required
def delete_collection(col_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM collection_videos WHERE collection_id=%s", (col_id,))
    cursor.execute("DELETE FROM collections WHERE id=%s", (col_id,))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/collections/<int:col_id>/videos', methods=['POST'])
@login_required
def add_video_to_collection(col_id):
    data = request.get_json()
    filename = data.get('filename', '').strip()
    if not filename: return jsonify({'error': 'Filename required'}), 400
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM videos WHERE filename=%s", (filename,))
    v = cursor.fetchone()
    if not v:
        cursor.close(); conn.close()
        return jsonify({'error': 'Video not found'}), 404
    try:
        cursor.execute("INSERT INTO collection_videos (collection_id, video_id) VALUES (%s, %s)", (col_id, v['id']))
        conn.commit()
    except mysql.connector.IntegrityError: pass
    cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/collections/<int:col_id>/videos/<filename>', methods=['DELETE'])
@login_required
def remove_video_from_collection(col_id, filename):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""DELETE cv FROM collection_videos cv
        JOIN videos v ON v.id=cv.video_id
        WHERE cv.collection_id=%s AND v.filename=%s""", (col_id, filename))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/collections/<int:col_id>', methods=['GET'])
@login_required
def get_collection(col_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM collections WHERE id=%s", (col_id,))
    col = cursor.fetchone()
    if not col:
        cursor.close(); conn.close()
        return jsonify({'error': 'Not found'}), 404
    cursor.execute("""SELECT v.* FROM videos v
        JOIN collection_videos cv ON v.id=cv.video_id
        WHERE cv.collection_id=%s ORDER BY cv.position, v.filename""", (col_id,))
    videos = [_db_row_to_video_dict(r) for r in cursor.fetchall()]
    cursor.close(); conn.close()
    return jsonify({'collection': col, 'videos': videos})

# ==================== Routes: Share ====================

@app.route('/api/video/<filename>/share', methods=['POST'])
@login_required
def create_share_token(filename):
    video_path = get_user_video_path(session['user_id'])
    fp = os.path.join(video_path, filename)
    if not os.path.exists(fp): return jsonify({'error': 'Not found'}), 404

    token = secrets.token_hex(16)
    hours = request.get_json().get('hours', 24) if request.is_json else 24
    expires = datetime.datetime.utcnow() + datetime.timedelta(hours=int(hours))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO share_tokens (token, video_filename, expires_at) VALUES (%s, %s, %s)",
                   (token, filename, expires))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({'success': True, 'token': token, 'url': f'/share/{token}', 'expires': str(expires)})

@app.route('/share/<token>')
def shared_video(token):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM share_tokens WHERE token=%s", (token,))
    share = cursor.fetchone()
    cursor.close(); conn.close()
    if not share: return "Invalid or expired share link", 404
    if share['expires_at'] and share['expires_at'] < datetime.datetime.utcnow():
        return "Share link has expired", 410
    # Use admin's video path
    return render_template('shared.html', video_filename=share['video_filename'],
                           token=token, title=os.path.splitext(share['video_filename'])[0])

# ==================== Routes: Dashboard ====================

@app.route('/dashboard')
@login_required
def dashboard():
    video_path = get_user_video_path(session['user_id'])
    _sync_and_get_videos(video_path)  # ensure up-to-date

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as cnt FROM videos")
    total_videos = cursor.fetchone()['cnt']

    cursor.execute("SELECT COALESCE(SUM(duration), 0) as total_duration FROM videos")
    total_duration = cursor.fetchone()['total_duration']

    cursor.execute("SELECT COALESCE(SUM(file_size), 0) as total_size FROM videos")
    total_size = cursor.fetchone()['total_size']

    cursor.execute("SELECT COALESCE(SUM(duration), 0) as watched FROM videos WHERE progress > 0")
    watched_duration = cursor.fetchone()['watched']

    cursor.execute("SELECT COUNT(*) as cnt FROM videos WHERE is_favorite = 1")
    favorites = cursor.fetchone()['cnt']

    cursor.execute("""SELECT t.name, t.color, COUNT(vt.video_id) as cnt FROM tags t
        JOIN video_tags vt ON t.id=vt.tag_id GROUP BY t.id ORDER BY cnt DESC LIMIT 20""")
    tag_stats = cursor.fetchall()

    cursor.execute("SELECT codec, COUNT(*) as cnt FROM videos WHERE codec != '' GROUP BY codec")
    codec_stats = cursor.fetchall()

    cursor.execute("""SELECT
        SUM(CASE WHEN width >= 3840 THEN 1 ELSE 0 END) as uhd,
        SUM(CASE WHEN width >= 1920 AND width < 3840 THEN 1 ELSE 0 END) as fhd,
        SUM(CASE WHEN width >= 1280 AND width < 1920 THEN 1 ELSE 0 END) as hd,
        SUM(CASE WHEN width > 0 AND width < 1280 THEN 1 ELSE 0 END) as sd
    FROM videos""")
    res_stats = cursor.fetchone()

    cursor.close(); conn.close()

    stats = {
        'total_videos': total_videos,
        'total_duration': total_duration,
        'total_duration_formatted': format_duration(total_duration),
        'total_size': total_size,
        'total_size_formatted': format_filesize(total_size),
        'watched_duration': watched_duration,
        'watched_duration_formatted': format_duration(watched_duration),
        'favorites': favorites,
        'tag_stats': tag_stats,
        'codec_stats': codec_stats,
        'res_stats': res_stats,
    }
    return render_template('dashboard.html', stats=stats)

# ==================== Routes: User ====================

@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, video_path FROM users WHERE username=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    return jsonify(user)

@app.route('/api/user/profile', methods=['POST'])
@login_required
def update_user_profile():
    data = request.get_json()
    username = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    updates, params = [], []

    new_username = data.get('username', '').strip()
    if new_username and new_username != username:
        cursor.execute("SELECT id FROM users WHERE username=%s AND username!=%s", (new_username, username))
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({'error': 'Username already exists'}), 400
        updates.append("username=%s"); params.append(new_username)
        session['user_id'] = new_username; session['username'] = new_username

    new_password = data.get('password', '').strip()
    if new_password:
        verify = data.get('verify_password', '').strip()
        if not verify: return jsonify({'error': 'Current password required'}), 400
        cursor.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not bcrypt.checkpw(verify.encode(), user['password_hash'].encode()):
            return jsonify({'error': 'Current password incorrect'}), 400
        updates.append("password_hash=%s"); params.append(bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode())

    vp = data.get('video_path', '').strip()
    if vp:
        updates.append("video_path=%s"); params.append(vp); session['video_path'] = vp

    if updates:
        params.append(username)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE username=%s", params)
        conn.commit()
    cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/settings')
@login_required
def settings_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, video_path FROM users WHERE username=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    return render_template('settings.html', user=user)

# ==================== Init ====================

if __name__ == '__main__':
    init_database()
    _init_db_pool()
    from waitress import serve
    serve(app, host='0.0.0.0', port=55300, threads=8, send_bytes=2097152)
