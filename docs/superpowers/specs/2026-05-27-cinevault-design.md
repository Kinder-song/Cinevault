# CineVault - Design Specification

## Project Overview
**Project Name:** CineVault
**Type:** Local Video Management & Streaming Website
**Core Functionality:** A beautifully designed local video library with streaming, thumbnail generation, tagging, and authentication.
**Target Users:** Single admin user managing a collection of local video files.

---

## Visual Design Direction

### Theme: "Cinematic Editorial Dark"
- **Glassmorphism Dark Mode** with subtle flowing light effects
- Deep void backgrounds with frosted glass cards
- Cold amber/neon frost blue accents for interactive elements

### Color Palette
| Role | Color |
|------|-------|
| Background Deep | `#090A0F`, `#13151F` |
| Glass Surface | `rgba(20, 22, 30, 0.6)`, border `rgba(255, 255, 255, 0.06)` |
| Accent Primary | `#D4A373` (cold amber) |
| Accent Secondary | `#6D8AFF` (neon frost blue) |
| Text Primary | `#FFFFFF` at 90% opacity |
| Text Secondary | `#FFFFFF` at 60% opacity |

### Typography
- **Font Family:** Outfit (Google Fonts CDN)
- **Headings:** font-weight 200, letter-spacing -0.02em
- **Body:** font-weight 400, line-height 1.6
- **Fallback Stack:** `Outfit, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

### Layout System
- **Homepage:** Bento Grid with auto-fill (minmax 320px, 1fr), gap 1.5rem
- **Player Page:** Centered, max-width 900px, black rounded container
- **Navigation:** Fixed top bar, 64px height, strong blur backdrop
- **Spacing Grid:** 4px/8px base unit system

---

## Key Design Decisions

### 1. Hover Light沙流动效果
- Mouse position tracked via JS
- CSS gradient follows cursor, creating flowing light effect on card edges
- Implemented even without real thumbnails for artistic effect

### 2. Bento Grid Layout
- Video cards arranged in masonry-style grid
- Mixed card sizes create visual rhythm
- Cards have `backdrop-filter: blur(12px)` glass effect

### 3. Tag Management: Inline Expansion
- Clicking tag area expands card downward to reveal tag editor
- Tags appear as frosted glass pills with subtle glow
- Add animation: tags "bubble up" from input with elastic easing

### 4. Login Page: Flowing Glow Background
- Multiple slow-moving soft light circles in background
- Colors: deep void + frost blue + amber tones
- Form centered with bottom-border style inputs

### 5. Video Thumbnails
- Use bundled ffmpeg to extract frames
- First frame as default thumbnail
- Refresh button randomizes extraction time point
- Fallback: animated gradient placeholder with play icon

---

## Technical Architecture

### Backend Stack
- **Python 3.10+**, **Flask** framework, **Jinja2** templates
- **MySQL** via `mysql-connector-python`
- **Flask-Session** with MySQL session storage
- **bcrypt** for password hashing

### Frontend Stack
- **Tailwind CSS** via CDN (customized extensively)
- **Pure HTML5 + CSS3 + Vanilla JS** (ES6)
- **Lucide Icons** via CDN
- **Outfit** font via Google Fonts CDN

### Video Processing
- Bundled `ffmpeg` binary at project root
- Thumbnail extraction: `ffmpeg -ss {time} -i {input} -vframes 1 {output}`
- Metadata extraction: `ffprobe -v quiet -show_entries format=duration,size -of json`

### API Design (All require authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Homepage with video grid |
| GET | `/login` | Login page |
| POST | `/login` | Login submission |
| GET | `/logout` | Logout |
| GET | `/video/<filename>` | Video player page |
| GET | `/api/videos` | Get all videos with tags |
| POST | `/api/video/<filename>/tags` | Add tag to video |
| DELETE | `/api/video/<filename>/tags/<tag>` | Remove tag |
| POST | `/api/video/<filename>/refresh-thumb` | Refresh thumbnail |
| GET | `/stream/<filename>` | Video streaming (Range support) |
| GET | `/thumbnail/<filename>` | Get thumbnail image |

### Database Schema

```sql
-- Videos table
CREATE TABLE videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(500),
    duration INT,
    size BIGINT,
    thumbnail_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags table
CREATE TABLE tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    color VARCHAR(20) DEFAULT '#7b9cff'
);

-- Video-Tag relationship (many-to-many)
CREATE TABLE video_tags (
    video_id INT,
    tag_id INT,
    PRIMARY KEY (video_id, tag_id)
);

-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);
```

### Authentication Flow
1. First run: auto-create admin/admin123
2. Login creates Flask session (stored in MySQL)
3. `@login_required` decorator protects all routes
4. Unauthenticated requests redirect to `/login`

---

## Interaction Details

### Video Card Interactions
- **Hover (0.5s delay):** Start muted video preview, show flowing light effect
- **Mouse leave:** Pause video, reset to start, restore static thumbnail
- **Click title/tag area:** Inline expand tag editor
- **Click card body:** Navigate to player page

### Player Controls
- Play/Pause (spacebar)
- Seek ±5s (left/right arrows)
- Volume ±10% (up/down arrows)
- Fullscreen toggle
- Playback speed (0.5x, 1x, 1.5x, 2x)

### Tag Management
- Input: Enter key submits new tag
- Delete: Click × button to remove
- Animation: Tags bubble up with elastic easing (cubic-bezier(0.34, 1.56, 0.64, 1))

### Error States
- Login error: Form shakes horizontally, input border turns red
- API error: Toast notification with error message
- Video not found: 404 page with navigation back

---

## File Structure

```
video_view/
├── app.py                    # Flask main application
├── config.py                 # Configuration loader
├── requirements.txt          # Python dependencies
├── README.md                 # Setup instructions
├── ffmpeg                    # Bundled ffmpeg binary
├── .env                      # Environment variables
├── video/                    # Video files directory
├── thumbnails/               # Generated thumbnails
├── static/
│   ├── css/
│   │   └── style.css        # All custom styles
│   └── js/
│       └── main.js          # All frontend interactions
└── templates/
    ├── base.html             # Base template with nav
    ├── index.html            # Homepage (Bento grid)
    ├── login.html            # Login page
    ├── video.html            # Player page
    └── components/
        └── video_card.html   # Video card component
```

---

## Dependencies

```
Flask==3.0.0
mysql-connector-python==8.2.0
bcrypt==4.1.2
Flask-Session==0.5.0
Werkzeug==3.0.1
```

---

## Implementation Notes

1. **ffmpeg path:** Use bundled `./ffmpeg` from project root
2. **Video path:** Loaded from `.env` (`video_path=./video`)
3. **Graceful degradation:** If thumbnail generation fails, show animated gradient placeholder
4. **Range requests:** Implement byte-range support for Safari/progress bar seeking
5. **Performance:** Limit concurrent video previews to 3 max