# CineVault

A beautifully designed local video management and streaming web application with a glassmorphism UI, metadata extraction, and full-featured video player.

![](https://img.shields.io/badge/Python-3.10+-blue) ![](https://img.shields.io/badge/Flask-3.0-green) ![](https://img.shields.io/badge/MySQL-8.0-orange)

## Features

### Video Library
- **Bento grid layout** with glassmorphism cards, hover previews, and flow-light effects
- **Grid / List view toggle** with localStorage persistence
- **Server-side pagination** with configurable page size (12/24/48/96)
- **Full-text search** across titles, tags, resolution, framerate, and bitrate
- **Sort** by name, file size, or date
- **Collection filter** — organize videos into named collections
- **Progress indicators** on cards showing watch completion percentage
- **Favorite** badges and **rating** display on cards

### Video Player
- **Custom controls**: play/pause, volume, speed (0.25x–2x), skip ±10s, progress bar
- **Theater mode** — expands player to full width with side-by-side metadata
- **Picture-in-Picture** support
- **Fullscreen** with complete keyboard control
- **Subtitle support** — auto-detects `.srt`, `.vtt`, `.ass` files alongside videos
- **Screenshot gallery** — auto-discovers related images with lightbox viewer
- **Playback progress memory** — auto-saves position every 5 seconds, resume bar on return
- **5-star rating** system with click-to-toggle
- **Favorite / bookmark** toggle
- **Share links** — generate time-limited tokens (1h / 24h / 3d / 7d) with copy-to-clipboard

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` / `K` | Play / Pause |
| `J` | Skip back 10s |
| `L` | Skip forward 10s |
| `←` `→` | Skip ±5s |
| `↑` `↓` | Volume ±10% |
| `F` | Fullscreen |
| `T` | Theater mode |
| `P` | Picture-in-Picture |
| `M` | Mute / Unmute |
| `0`–`9` | Seek to 0%–90% |

### Dashboard
- **Stats cards**: total videos, total duration, total storage, favorites, watch progress
- **Charts**: tag distribution, codec distribution, resolution breakdown (4K / 1080p / 720p / SD)

### Metadata & Organization
- **Automatic metadata extraction** via ffmpeg: resolution, framerate, bitrate, video/audio codec, channels, sample rate
- **Incremental sync** — only re-scans files when size or modification time changes
- **Thumbnail generation** — random frame capture, manual refresh
- **Tag system** — add/remove tags with color-coded pills on cards and player page
- **Collections** — create, delete, add/remove videos (many-to-many)

### Theme & UX
- **Dark / Light theme** toggle with localStorage persistence
- **Glassmorphism design** — backdrop-filter blur on cards, nav, panels
- **Toast notifications** — slide-in alerts for all actions (success/error/info)
- **Mobile responsive** — adaptive layout at 768px and 480px breakpoints
- **Lazy-loaded hover previews** — video thumbnails animate into muted previews on hover

### Performance
- **Waitress production WSGI server** — 8 worker threads, 2MB socket buffer
- **2MB file I/O buffer** — eliminates ~250x system calls vs default 8KB buffer
- **Incremental DB sync** — batch-stat comparison, ffmpeg only on new/changed files
- **MySQL connection pooling** — 8 persistent connections
- **RAF-batched DOM updates** — timeupdate handler uses requestAnimationFrame
- **Hardware video overlay path** — no GPU compositing hacks on video element
- **Debounced search** — 100ms delay, CSS class toggle instead of display:none

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask 3.0 |
| WSGI Server | Waitress 3.0 |
| Database | MySQL 8.0, mysql-connector-python |
| Auth | bcrypt password hashing, Flask sessions |
| Frontend | Jinja2 templates, vanilla JavaScript, Tailwind CSS (CDN) |
| Icons | Lucide (lazy-loaded) |
| Video | ffmpeg (metadata extraction, thumbnail generation) |

## Prerequisites

- Python 3.10+
- MySQL 8.0+
- ffmpeg (included as `./ffmpeg` binary or set custom path)

## Setup

### 1. Clone and create virtual environment
```bash
git clone https://github.com/Kinder-song/Cinevault.git
cd Cinevault
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
```

Edit `.env` with your settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret | `cinevault-secret-key-...` |
| `DB_HOST` | MySQL host | `localhost` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_USER` | MySQL user | `root` |
| `DB_PASSWORD` | MySQL password | (empty) |
| `DB_NAME` | Database name | `video` |
| `video_path` | Video files directory | `./video` |
| `FFMPEG_PATH` | ffmpeg binary path | `./ffmpeg` |

### 4. Place video files
Put your `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, or `.m4v` files in the `video/` directory (or the path configured in `.env`).

### 5. Run
```bash
python app.py
```

The application starts at **http://localhost:55300**.

### Default credentials
- **Username**: `admin`
- **Password**: `admin123`

> Change the password immediately via the Settings page after first login.

## Project Structure

```
Cinevault/
├── app.py                  # Main application (982 lines)
├── config.py               # Environment configuration
├── requirements.txt        # Python dependencies
├── ffmpeg                  # ffmpeg binary
├── .env                    # Environment variables (gitignored)
├── static/
│   ├── css/style.css       # Full stylesheet (2378 lines)
│   └── js/main.js          # Client-side logic (541 lines)
├── templates/
│   ├── base.html           # Base layout with nav, theme, CDN loading
│   ├── index.html          # Video library with pagination + filters
│   ├── video.html          # Video player page
│   ├── dashboard.html      # Stats and charts dashboard
│   ├── shared.html         # Public share page (no auth)
│   ├── login.html          # Login form
│   └── settings.html       # User settings
├── video/                  # Video files directory (gitignored)
├── thumbnails/             # Generated thumbnails (gitignored)
├── sessions/               # Flask session files (gitignored)
└── cache/                  # Metadata cache (gitignored)
```

## API Reference

### Video Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/video/<f>/tags` | Add tag to video |
| `DELETE` | `/api/video/<f>/tags/<t>` | Remove tag from video |
| `POST` | `/api/video/<f>/progress` | Save playback position |
| `POST` | `/api/video/<f>/favorite` | Toggle favorite |
| `POST` | `/api/video/<f>/rating` | Set rating (0–5) |
| `POST` | `/api/video/<f>/refresh-thumb` | Regenerate thumbnail |
| `GET` | `/api/video/<f>/info` | Get video metadata |
| `POST` | `/api/video/<f>/share` | Create share link |

### Collections
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/collections` | List all collections |
| `POST` | `/api/collections` | Create collection |
| `DELETE` | `/api/collections/<id>` | Delete collection |
| `GET` | `/api/collections/<id>` | Get collection with videos |
| `POST` | `/api/collections/<id>/videos` | Add video to collection |
| `DELETE` | `/api/collections/<id>/videos/<f>` | Remove video from collection |

### User
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/user/profile` | Get user profile |
| `POST` | `/api/user/profile` | Update username/password/video path |

## Supported Formats

### Video
`.mp4` `.mkv` `.webm` `.mov` `.avi` `.m4v`

### Subtitles (auto-detected alongside video files)
`.srt` `.vtt` `.ass`

### Screenshots (auto-detected by filename prefix match)
`.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp`
