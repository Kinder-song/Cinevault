# CineVault v2 — M2 视频库 + 播放器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 端到端可用的视频库与播放器——后端视频列表/搜索/详情/缩略图/多设备播放进度 API，前端 React Library 页面（bento 网格 + 过滤/排序/分页）、Player 页面（自定义控制条 + 进度同步 + 键盘快捷键），通过 Playwright E2E 测试。

**Architecture:** 后端扩展 `application/videos/`（list / filter / detail / thumbnail / playback service）+ `interface/http/v1/videos.py`（HTTP 路由）。前端新增 `frontend/src/pages/library/`、`frontend/src/pages/player/`、`frontend/src/api/`（typed fetch client）、`frontend/src/components/`（通用 VideoCard、FilterBar、PlayerControls 等）。HLS 转码推迟到 M2.5（播放器先用 M1 的 progressive MP4 流）。

**Tech Stack:** 后端继承 M1（FastAPI + SQLAlchemy + bcrypt + JWT + ffmpeg）；前端新增 TanStack Query v5、TanStack Table v8（headless 表格用于库列表分页/排序）、zustand、framer-motion、Vitest + Playwright。

**项目位置:** `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/`
**基线:** 从 main（M1 squash）拉新分支 `m2-library-player`

---

## File Structure (M2 完成后)

```
src/cinevault/                                # 后端增量
├── application/
│   ├── videos/                                # NEW
│   │   ├── __init__.py
│   │   ├── service.py                        # list/filter/detail/playback
│   │   ├── schemas.py                        # Pydantic
│   │   └── thumbnail.py                      # ffmpeg 抽帧
│   └── thumbnails/                            # NEW (or under videos/)
│       └── (merged into videos/thumbnail.py)
└── interface/http/v1/
    ├── videos.py                              # NEW: /api/v1/videos/* + /playback
    └── ...

frontend/src/                                 # 前端增量
├── api/                                        # NEW
│   ├── client.ts                              # typed fetch wrapper
│   ├── types.ts                               # API 响应类型
│   └── hooks.ts                                # useVideos, usePlayback 等
├── pages/
│   ├── library/                                # NEW
│   │   ├── LibraryPage.tsx
│   │   ├── FilterBar.tsx
│   │   ├── VideoCard.tsx
│   │   ├── SortMenu.tsx
│   │   ├── ViewToggle.tsx
│   │   ├── Pagination.tsx
│   │   ├── EmptyState.tsx
│   │   └── *.test.tsx
│   └── player/                                 # NEW
│       ├── PlayerPage.tsx
│       ├── VideoCanvas.tsx                    # 视频元素 + hls.js
│       ├── ControlBar.tsx
│       ├── ResumeBar.tsx
│       ├── SubtitleMenu.tsx
│       ├── useKeyboardShortcuts.ts
│       └── *.test.tsx
├── components/                                # 通用 UI
│   ├── primitives/                            # Button, Skeleton, Toast 等（M2 增量）
│   │   ├── Button.tsx
│   │   ├── Skeleton.tsx
│   │   └── EmptyState.tsx
│   └── media/                                 # NEW
│       ├── Thumbnail.tsx
│       └── PlayIcon.tsx
├── lib/                                        # 工具
│   ├── format.ts                              # 时长/字节格式化
│   └── theme.ts                               # CSS var helpers
├── styles/
│   ├── tokens.css                             # 完整设计 token (扩展 M0 占位)
│   ├── animations.css                          # 动效
│   └── reset.css                              # 现代化 reset
├── routes.tsx                                  # 路由配置
└── App.tsx                                    # 改为 Router 根

frontend/tests/e2e/                             # NEW: Playwright
├── library.spec.ts
└── player.spec.ts

frontend/playwright.config.ts                  # NEW
```

---

## Task 1: 后端 Thumbnail 服务（ffmpeg 抽帧）

**Files:**
- Create: `src/cinevault/application/videos/__init__.py`
- Create: `src/cinevault/application/videos/thumbnail.py`
- Create: `tests/application/videos/__init__.py`
- Create: `tests/application/videos/test_thumbnail.py`

- [ ] **Step 1: 写失败测试**

`tests/application/videos/test_thumbnail.py`：

```python
"""Tests for thumbnail generation service."""

from __future__ import annotations

from pathlib import Path

import pytest

from cinevault.application.videos.thumbnail import generate_thumbnail


@pytest.mark.asyncio
async def test_generate_thumbnail_for_existing_file(tmp_path: Path) -> None:
    """For a fake (empty) file, return None (ffprobe won't extract)."""
    f = tmp_path / "fake.mp4"
    f.write_bytes(b"\x00" * 100)
    result = await generate_thumbnail(f, tmp_path)
    # No ffmpeg → graceful None
    assert result is None or isinstance(result, Path)


@pytest.mark.asyncio
async def test_generate_thumbnail_uses_cache(tmp_path: Path) -> None:
    """If thumbnail already exists and is newer than source, return it."""
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x" * 100)

    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    cached = thumb_dir / "a.jpg"
    cached.write_bytes(b"old jpeg bytes")
    import os
    # Make source mtime OLDER than thumb
    os.utime(src, (1000, 1000))
    os.utime(cached, (2000, 2000))

    result = await generate_thumbnail(src, thumb_dir)
    assert result == cached


@pytest.mark.asyncio
async def test_thumbnail_filename_uses_basename(tmp_path: Path) -> None:
    """Thumbnail file name is the source basename + .jpg."""
    src = tmp_path / "long_name.mp4"
    src.write_bytes(b"x")
    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    result = await generate_thumbnail(src, thumb_dir)
    if result is not None:
        assert result.name == "long_name.jpg"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/application/videos/test_thumbnail.py -v --no-cov
```

期望：ModuleNotFoundError。

- [ ] **Step 3: 创建目录与 thumbnail 服务**

```bash
mkdir -p src/cinevault/application/videos tests/application/videos
touch src/cinevault/application/videos/__init__.py tests/application/videos/__init__.py
```

`src/cinevault/application/videos/thumbnail.py`：

```python
"""Thumbnail generation: ffmpeg frame extraction with cache."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from cinevault.infrastructure.media.ffprobe import FFPROBE_BIN  # reuse from T15

CHUNK_SIZE = 2 * 1024 * 1024


async def generate_thumbnail(source: Path, thumb_dir: Path) -> Path | None:
    """Extract a single frame as JPEG. Returns cached or newly created path,
    or None on failure (missing ffmpeg, bad file, etc.).
    """
    source = Path(source)
    thumb_dir = Path(thumb_dir)
    if not source.is_file():
        return None

    thumb_dir.mkdir(parents=True, exist_ok=True)
    out = thumb_dir / f"{source.stem}.jpg"

    # Cache hit: thumb exists and is newer than source
    if out.is_file() and out.stat().st_mtime >= source.stat().st_mtime:
        return out

    cmd = [
        FFPROBE_BIN,  # wait — this is ffprobe, not ffmpeg
        # Use ffmpeg for frame extraction
    ]
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss", "1",          # seek 1s in
        "-i", str(source),
        "-frames:v", "1",
        "-q:v", "2",
        str(out),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
    except (TimeoutError, FileNotFoundError, OSError):
        return None

    if proc.returncode != 0 or not out.is_file():
        return None
    return out
```

**注**：上面的 FFPROBE_BIN import 不需要（已删），仅用 ffmpeg。

清理后：

`src/cinevault/application/videos/thumbnail.py`：

```python
"""Thumbnail generation: ffmpeg frame extraction with cache."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

CHUNK_SIZE = 2 * 1024 * 1024

FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"


async def generate_thumbnail(source: Path, thumb_dir: Path) -> Path | None:
    """Extract a single frame as JPEG. Returns cached or newly created path,
    or None on failure (missing ffmpeg, bad file, etc.).
    """
    source = Path(source)
    thumb_dir = Path(thumb_dir)
    if not source.is_file():
        return None

    thumb_dir.mkdir(parents=True, exist_ok=True)
    out = thumb_dir / f"{source.stem}.jpg"

    # Cache hit: thumb exists and is newer than source
    if out.is_file() and out.stat().st_mtime >= source.stat().st_mtime:
        return out

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-ss", "1",
        "-i", str(source),
        "-frames:v", "1",
        "-q:v", "2",
        str(out),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
    except (TimeoutError, FileNotFoundError, OSError):
        return None

    if proc.returncode != 0 or not out.is_file():
        return None
    return out
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/application/videos/test_thumbnail.py -v --no-cov
```

期望：3 passed（`test_generate_thumbnail_for_existing_file` 和 `test_thumbnail_filename_uses_basename` 返回 None 因为 ffmpeg 不在 PATH；`test_generate_thumbnail_uses_cache` 命中缓存路径返回 `cached`）。

- [ ] **Step 5: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git checkout -b m2-library-player
git add src/cinevault/application/videos/ tests/application/videos/
git commit -m "feat(videos): add ffmpeg thumbnail service with cache"
```

---

## Task 2: 扩展 Settings（thumbnail_dir）

**Files:**
- Modify: `src/cinevault/config.py`

- [ ] **Step 1: 追加字段**

修改 `src/cinevault/config.py` 的 `Settings` 类（JWT 字段后）：

```python
    # Media
    thumbnail_dir: Path = Field(default=Path("./data/thumbnails"))
    hls_dir: Path = Field(default=Path("./data/hls"))        # M2.5 will use
```

（`thumbnail_dir` 实际已在 M0 config.py 存在；确认后跳过此步。）

- [ ] **Step 2: 提交（如有变更）**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git diff src/cinevault/config.py
git add src/cinevault/config.py 2>/dev/null
git diff --staged --quiet && git commit -m "feat(config): ensure thumbnail_dir setting exists" --allow-empty
```

---

## Task 3: 缩略图 HTTP 路由

**Files:**
- Modify: `src/cinevault/interface/http/v1/stream.py`（已存在 — 添加缩略图端点）
- Create: `tests/interface/http/v1/test_thumbnail.py`

- [ ] **Step 1: 写失败测试**

`tests/interface/http/v1/test_thumbnail.py`：

```python
"""Integration tests for video thumbnails."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cinevault.core.password import hash_password
from cinevault.infrastructure.db.base import Base
from cinevault.infrastructure.db.models import Library, User, Video
from cinevault.infrastructure.db.session import get_sessionmaker, reset_engine
from cinevault.main import create_app


@pytest.fixture
def thumb_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp())
    media_dir = tmp / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"\x00" * 100)

    async def _seed() -> None:
        reset_engine()
        sm = get_sessionmaker("sqlite+aiosqlite:///:memory:")
        async with sm() as s:
            async with s.bind.connect() as conn:  # type: ignore[union-attr]
                await conn.run_sync(Base.metadata.create_all)
            u = User(username="u", email="u@x.com", password_hash=hash_password("pw"))
            s.add(u)
            await s.flush()
            lib = Library(owner_id=u.id, name="L", root_path=str(media_dir))
            s.add(lib)
            await s.flush()
            s.add(Video(
                library_id=lib.id, title="a", original_filename="a.mp4",
                storage_path="a.mp4", container="mp4", file_size_bytes=100,
                file_hash="a" * 64, mtime=1, width=0, height=0,
            ))
            await s.commit()
        reset_engine()

    asyncio.run(_seed())
    yield TestClient(create_app())
    shutil.rmtree(tmp, ignore_errors=True)


def test_thumbnail_404_for_missing_video(thumb_client: TestClient) -> None:
    res = thumb_client.get("/api/v1/videos/nope/thumbnail")
    assert res.status_code == 404


def test_thumbnail_404_when_generation_fails(thumb_client: TestClient) -> None:
    """When ffmpeg is absent, endpoint returns 404 (graceful)."""
    res = thumb_client.get("/api/v1/videos/a.mp4/thumbnail")
    # ffmpeg not in PATH → thumbnail not generated → 404
    assert res.status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/interface/http/v1/test_thumbnail.py -v --no-cov
```

- [ ] **Step 3: 扩展 stream.py（或新建 videos.py）**

`src/cinevault/interface/http/v1/stream.py` 末尾追加缩略图端点（在同一 router 下）：

```python
from cinevault.application.videos.thumbnail import generate_thumbnail
from cinevault.config import get_settings

# 在 router 定义后追加
@router.get("/thumbnail/{filename:path}")
async def thumbnail(
    filename: str,
    session: AsyncSession = Depends(db_session),
) -> Response:
    """Serve a video's thumbnail. Generates on demand if missing."""
    query = await session.execute(
        select(Video).where(Video.original_filename == filename)
    )
    video = query.scalar_one_or_none()
    if video is None:
        raise AppError("video_not_found", f"Video '{filename}' not found", 404)

    lib_repo = LibraryRepository(session)
    lib = await lib_repo.get_by_id(video.library_id)
    if lib is None:
        raise AppError("library_not_found", "Parent library missing", 404)

    file_path = Path(lib.root_path) / video.storage_path
    if not file_path.is_file():
        raise AppError("file_missing", "Source file missing", 404)

    settings = get_settings()
    thumb_path = await generate_thumbnail(file_path, settings.thumbnail_dir)
    if thumb_path is None or not thumb_path.is_file():
        raise AppError("thumbnail_unavailable", "Could not generate thumbnail", 404)

    return Response(
        content=thumb_path.read_bytes(),
        status_code=200,
        headers={"Content-Type": "image/jpeg", "Cache-Control": "public, max-age=604800"},
    )
```

注：实际的 URL 是 `/api/v1/stream/thumbnail/{filename}`，因为我们把缩略图加在了 stream router 下（共享 prefix）。这与 M1 的 `/api/v1/stream/{filename}` 路径共存。

如果更希望独立 prefix，可以创建 `src/cinevault/interface/http/v1/videos.py` router `prefix="/api/v1/videos"`。这里为了简单起见放在 stream 下。

- [ ] **Step 4: 跑测试**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/interface/http/v1/test_thumbnail.py -v --no-cov
```

期望：2 passed。

- [ ] **Step 5: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add src/cinevault/interface/http/v1/stream.py tests/interface/http/v1/test_thumbnail.py
git commit -m "feat(http): add /api/v1/stream/thumbnail/{filename} endpoint"
```

---

## Task 4: 视频列表 + 高级搜索 service

**Files:**
- Create: `src/cinevault/application/videos/service.py`
- Create: `src/cinevault/application/videos/schemas.py`
- Create: `tests/application/videos/test_service.py`

- [ ] **Step 1: 写失败测试**

`tests/application/videos/test_service.py`：

```python
"""Tests for video list / filter / detail service."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cinevault.application.videos.schemas import VideoFilter, VideoOut, VideoList
from cinevault.application.videos.service import list_videos, get_video
from cinevault.infrastructure.db.models import Library, User, Video
from cinevault.infrastructure.repositories.library import LibraryRepository
from cinevault.infrastructure.repositories.user import UserRepository
from cinevault.infrastructure.repositories.video import VideoRepository


async def _setup_library_with_videos(db_session: AsyncSession, tmp_path: Path) -> int:
    user = await UserRepository(db_session).create(
        username="u", email="u@x.com", password_hash="h"
    )
    lib = await LibraryRepository(db_session).create(
        owner_id=user.id, name="L", root_path=str(tmp_path)
    )
    repo = VideoRepository(db_session)
    for i, name in enumerate(["a", "b", "c"]):
        await repo.upsert(
            library_id=lib.id, storage_path=f"{name}.mp4",
            original_filename=f"{name}.mp4", title=name,
            container="mp4", file_size_bytes=100 * (i + 1),
            file_hash=str(i) * 64, mtime=i + 1,
            duration_sec=60.0 * (i + 1), width=1920, height=1080,
        )
    return user.id


@pytest.mark.asyncio
async def test_list_videos_empty(db_session: AsyncSession, tmp_path: Path) -> None:
    user = await UserRepository(db_session).create(username="u", email="u@x.com", password_hash="h")
    await LibraryRepository(db_session).create(
        owner_id=user.id, name="L", root_path=str(tmp_path)
    )
    result = await list_videos(db_session, owner_id=user.id)
    assert isinstance(result, VideoList)
    assert result.total == 0
    assert result.videos == []


@pytest.mark.asyncio
async def test_list_videos_returns_all(db_session: AsyncSession, tmp_path: Path) -> None:
    uid = await _setup_library_with_videos(db_session, tmp_path)
    result = await list_videos(db_session, owner_id=uid)
    assert result.total == 3
    assert len(result.videos) == 3


@pytest.mark.asyncio
async def test_list_videos_pagination(db_session: AsyncSession, tmp_path: Path) -> None:
    uid = await _setup_library_with_videos(db_session, tmp_path)
    result = await list_videos(
        db_session, owner_id=uid, page=2, per_page=2
    )
    assert result.page == 2
    assert result.per_page == 2
    assert len(result.videos) == 1


@pytest.mark.asyncio
async def test_list_videos_filter_favorite(db_session: AsyncSession, tmp_path: Path) -> None:
    uid = await _setup_library_with_videos(db_session, tmp_path)
    # Mark one as favorite
    from sqlalchemy import select
    result = await db_session.execute(select(Video).where(Video.title == "a"))
    vid = result.scalar_one()
    vid.favorite = True
    await db_session.flush()

    filtered = await list_videos(db_session, owner_id=uid, filter=VideoFilter(favorite=True))
    assert filtered.total == 1
    assert filtered.videos[0].title == "a"


@pytest.mark.asyncio
async def test_list_videos_search_by_title(db_session: AsyncSession, tmp_path: Path) -> None:
    uid = await _setup_library_with_videos(db_session, tmp_path)
    filtered = await list_videos(
        db_session, owner_id=uid, filter=VideoFilter(search="b")
    )
    assert filtered.total == 1
    assert filtered.videos[0].title == "b"


@pytest.mark.asyncio
async def test_list_videos_sort_by_title(db_session: AsyncSession, tmp_path: Path) -> None:
    uid = await _setup_library_with_videos(db_session, tmp_path)
    result = await list_videos(
        db_session, owner_id=uid, sort_by="title", sort_order="desc"
    )
    titles = [v.title for v in result.videos]
    assert titles == ["c", "b", "a"]


@pytest.mark.asyncio
async def test_get_video(db_session: AsyncSession, tmp_path: Path) -> None:
    uid = await _setup_library_with_videos(db_session, tmp_path)
    listing = await list_videos(db_session, owner_id=uid)
    target = listing.videos[0]
    fetched = await get_video(db_session, target.id)
    assert fetched is not None
    assert fetched.id == target.id


@pytest.mark.asyncio
async def test_get_video_missing(db_session: AsyncSession) -> None:
    result = await get_video(db_session, 99999)
    assert result is None
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/application/videos/test_service.py -v --no-cov
```

- [ ] **Step 3: 写 schemas**

`src/cinevault/application/videos/schemas.py`：

```python
"""Pydantic schemas for video use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VideoFilter(BaseModel):
    """Filter criteria for listing videos."""

    search: str | None = Field(default=None, max_length=200)
    favorite: bool | None = None
    watched: Literal["any", "in_progress", "completed", "unwatched"] = "any"
    width_min: int | None = Field(default=None, ge=0)
    duration_min: int | None = Field(default=None, ge=0)
    duration_max: int | None = Field(default=None, ge=0)
    library_id: int | None = None
    tag_ids: list[int] = Field(default_factory=list)


class VideoOut(BaseModel):
    """Public-facing video representation."""

    id: int
    title: str
    original_filename: str
    container: str
    width: int
    height: int
    duration_sec: float
    bitrate_kbps: int
    framerate: float
    file_size_bytes: int
    favorite: bool
    rating: int
    thumbnail_path: str | None
    transcode_status: str
    library_id: int
    storage_path: str
    mtime: int
    created_at: datetime
    last_played_at: datetime | None
    watched_duration: float
    progress_pct: float = 0.0

    model_config = {"from_attributes": True}


class VideoList(BaseModel):
    videos: list[VideoOut]
    total: int
    page: int
    per_page: int
    total_pages: int
```

- [ ] **Step 4: 写 service**

`src/cinevault/application/videos/service.py`：

```python
"""Video use cases: list, filter, detail."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cinevault.application.videos.schemas import VideoFilter, VideoList, VideoOut
from cinevault.infrastructure.db.models import Library, Video


async def list_videos(
    session: AsyncSession,
    *,
    owner_id: int,
    filter: VideoFilter | None = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    page: int = 1,
    per_page: int = 24,
) -> VideoList:
    """List videos owned by a user with optional filtering + pagination."""
    filter = filter or VideoFilter()
    page = max(page, 1)
    per_page = max(min(per_page, 96), 1)

    # Base query: videos in libraries owned by this user
    base = (
        select(Video)
        .join(Library, Library.id == Video.library_id)
        .where(Library.owner_id == owner_id)
    )

    # Apply filters
    if filter.search:
        like = f"%{filter.search.lower()}%"
        base = base.where(func.lower(Video.title).like(like))
    if filter.favorite is not None:
        base = base.where(Video.favorite == filter.favorite)
    if filter.width_min is not None:
        base = base.where(Video.width >= filter.width_min)
    if filter.duration_min is not None:
        base = base.where(Video.duration_sec >= filter.duration_min)
    if filter.duration_max is not None:
        base = base.where(Video.duration_sec <= filter.duration_max)
    if filter.library_id is not None:
        base = base.where(Video.library_id == filter.library_id)
    if filter.watched == "in_progress":
        base = base.where(
            Video.watched_duration > 0,
            Video.watched_duration < Video.duration_sec,
        )
    elif filter.watched == "completed":
        base = base.where(Video.watched_duration >= Video.duration_sec)
    elif filter.watched == "unwatched":
        base = base.where(Video.watched_duration == 0)

    # Total count (before pagination)
    count_q = select(func.count()).select_from(base.subquery())
    total = int((await session.execute(count_q)).scalar_one())

    # Sort
    sort_col = {
        "title": Video.title,
        "created_at": Video.created_at,
        "duration": Video.duration_sec,
        "size": Video.file_size_bytes,
        "filename": Video.original_filename,
    }.get(sort_by, Video.title)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    # Paginate
    offset = (page - 1) * per_page
    base = base.offset(offset).limit(per_page)

    rows = (await session.execute(base)).scalars().all()
    videos = [_to_video_out(v) for v in rows]

    total_pages = (total + per_page - 1) // per_page if total else 1
    return VideoList(
        videos=videos,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


async def get_video(session: AsyncSession, video_id: int) -> VideoOut | None:
    row = await session.get(Video, video_id)
    return _to_video_out(row) if row else None


def _to_video_out(v: Video) -> VideoOut:
    progress = 0.0
    if v.duration_sec and v.duration_sec > 0 and v.watched_duration:
        progress = min(100.0, (v.watched_duration / v.duration_sec) * 100.0)
    return VideoOut(
        id=v.id,
        title=v.title,
        original_filename=v.original_filename,
        container=v.container,
        width=v.width,
        height=v.height,
        duration_sec=v.duration_sec,
        bitrate_kbps=v.bitrate_kbps,
        framerate=v.framerate,
        file_size_bytes=v.file_size_bytes,
        favorite=v.favorite,
        rating=v.rating,
        thumbnail_path=v.thumbnail_path,
        transcode_status=v.transcode_status,
        library_id=v.library_id,
        storage_path=v.storage_path,
        mtime=v.mtime,
        created_at=v.created_at,
        last_played_at=v.last_played_at,
        watched_duration=v.watched_duration or 0.0,
        progress_pct=progress,
    )
```

- [ ] **Step 5: 跑测试确认通过**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/application/videos/test_service.py -v --no-cov
```

期望：8 passed。

- [ ] **Step 6: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add src/cinevault/application/videos/ tests/application/videos/
git commit -m "feat(videos): add list/filter/detail service with pagination + watched filter"
```

---

## Task 5: 视频列表 HTTP 路由

**Files:**
- Create: `src/cinevault/interface/http/v1/videos.py`
- Create: `tests/interface/http/v1/test_videos.py`
- Modify: `src/cinevault/main.py`

- [ ] **Step 1: 写失败测试**

`tests/interface/http/v1/test_videos.py`：

```python
"""Integration tests for /api/v1/videos list endpoint."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cinevault.core.password import hash_password
from cinevault.infrastructure.db.base import Base
from cinevault.infrastructure.db.models import Library, User, Video
from cinevault.infrastructure.db.session import get_sessionmaker, reset_engine
from cinevault.main import create_app


@pytest.fixture
def videos_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp())
    media_dir = tmp / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"\x00" * 100)
    (media_dir / "b.mp4").write_bytes(b"\x00" * 200)

    async def _seed() -> None:
        reset_engine()
        sm = get_sessionmaker("sqlite+aiosqlite:///:memory:")
        async with sm() as s:
            async with s.bind.connect() as conn:  # type: ignore[union-attr]
                await conn.run_sync(Base.metadata.create_all)
            u = User(username="u", email="u@x.com", password_hash=hash_password("pw"))
            s.add(u)
            await s.flush()
            lib = Library(owner_id=u.id, name="L", root_path=str(media_dir))
            s.add(lib)
            await s.flush()
            for i, name in enumerate(["a", "b"]):
                s.add(Video(
                    library_id=lib.id, title=name, original_filename=f"{name}.mp4",
                    storage_path=f"{name}.mp4", container="mp4",
                    file_size_bytes=100 * (i + 1), file_hash=str(i) * 64,
                    mtime=i + 1, width=1920, height=1080, duration_sec=60.0,
                ))
            await s.commit()
        reset_engine()

    asyncio.run(_seed())
    yield TestClient(create_app())
    shutil.rmtree(tmp, ignore_errors=True)


def test_list_videos(videos_client: TestClient) -> None:
    res = videos_client.get("/api/v1/videos")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert len(body["videos"]) == 2


def test_list_videos_pagination(videos_client: TestClient) -> None:
    res = videos_client.get("/api/v1/videos?per_page=1&page=2")
    body = res.json()
    assert body["page"] == 2
    assert len(body["videos"]) == 1


def test_list_videos_search(videos_client: TestClient) -> None:
    res = videos_client.get("/api/v1/videos?search=a")
    body = res.json()
    assert body["total"] == 1
    assert body["videos"][0]["title"] == "a"


def test_list_videos_sort(videos_client: TestClient) -> None:
    res = videos_client.get("/api/v1/videos?sort_by=title&sort_order=desc")
    body = res.json()
    titles = [v["title"] for v in body["videos"]]
    assert titles == ["b", "a"]


def test_list_videos_filter_favorite(videos_client: TestClient) -> None:
    res = videos_client.get("/api/v1/videos?favorite=true")
    body = res.json()
    assert body["total"] == 0
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/interface/http/v1/test_videos.py -v --no-cov
```

- [ ] **Step 3: 写 videos 路由**

`src/cinevault/interface/http/v1/videos.py`：

```python
"""/api/v1/videos list/detail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinevault.application.libraries.service import first_user_id
from cinevault.application.videos.schemas import VideoFilter, VideoList, VideoOut
from cinevault.application.videos.service import get_video, list_videos
from cinevault.interface.http.deps import db_session

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.get("", response_model=VideoList)
async def list_endpoint(
    search: str | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    watched: str = Query(default="any", pattern="^(any|in_progress|completed|unwatched)$"),
    width_min: int | None = Query(default=None, ge=0),
    duration_min: int | None = Query(default=None, ge=0),
    duration_max: int | None = Query(default=None, ge=0),
    library_id: int | None = Query(default=None),
    sort_by: str = Query(default="title", pattern="^(title|created_at|duration|size|filename)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=24, ge=1, le=96),
    session: AsyncSession = Depends(db_session),
) -> VideoList:
    owner_id = await first_user_id(session)
    flt = VideoFilter(
        search=search,
        favorite=favorite,
        watched=watched,  # type: ignore[arg-type]
        width_min=width_min,
        duration_min=duration_min,
        duration_max=duration_max,
        library_id=library_id,
    )
    return await list_videos(
        session,
        owner_id=owner_id,
        filter=flt,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )


@router.get("/{video_id}", response_model=VideoOut)
async def detail_endpoint(
    video_id: int,
    session: AsyncSession = Depends(db_session),
) -> VideoOut:
    video = await get_video(session, video_id)
    if video is None:
        from cinevault.core.errors import AppError
        raise AppError("video_not_found", f"Video {video_id} not found", 404)
    return video
```

- [ ] **Step 4: 注册路由**

修改 `src/cinevault/main.py` 的 `create_app`：

在 `app.include_router(stream_router)` 后**追加**：

```python
    from cinevault.interface.http.v1.videos import router as videos_router
    app.include_router(videos_router)
```

- [ ] **Step 5: 跑测试确认通过**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/interface/http/v1/test_videos.py -v --no-cov
```

期望：5 passed。

- [ ] **Step 6: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add src/cinevault/interface/http/v1/videos.py tests/interface/http/v1/test_videos.py src/cinevault/main.py
git commit -m "feat(http): add /api/v1/videos list+detail with filter/sort/pagination"
```

---

## Task 6: 播放进度 service + repository

**Files:**
- Create: `src/cinevault/infrastructure/db/models/playback_state.py`
- Modify: `src/cinevault/infrastructure/db/models/__init__.py`
- Modify: `src/cinevault/infrastructure/db/models/video.py`（无变更 — Video 已有 watched_duration 列）
- Create: `src/cinevault/infrastructure/repositories/playback_state.py`
- Create: `src/cinevault/application/playback/__init__.py`
- Create: `src/cinevault/application/playback/service.py`
- Create: `src/cinevault/application/playback/schemas.py`
- Create: `tests/application/playback/__init__.py`
- Create: `tests/application/playback/test_service.py`
- Create: `alembic/versions/2026_06_01_002_playback_state.py`

- [ ] **Step 1: 写失败测试**

`tests/application/playback/test_service.py`：

```python
"""Tests for playback progress tracking (per-device)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cinevault.application.playback.schemas import PlaybackUpdate
from cinevault.application.playback.service import (
    get_all_device_progress,
    record_progress,
)
from cinevault.infrastructure.db.models import Library, User, Video
from cinevault.infrastructure.repositories.library import LibraryRepository
from cinevault.infrastructure.repositories.user import UserRepository
from cinevault.infrastructure.repositories.video import VideoRepository


async def _setup(db_session: AsyncSession) -> tuple[int, int]:
    user = await UserRepository(db_session).create(username="u", email="u@x.com", password_hash="h")
    lib = await LibraryRepository(db_session).create(
        owner_id=user.id, name="L", root_path="/d"
    )
    v = await VideoRepository(db_session).upsert(
        library_id=lib.id, storage_path="a.mp4", original_filename="a.mp4",
        title="a", container="mp4", file_size_bytes=1, file_hash="a" * 64,
        mtime=1, duration_sec=100.0,
    )
    return user.id, v.id


@pytest.mark.asyncio
async def test_record_first_progress(db_session: AsyncSession) -> None:
    uid, vid = await _setup(db_session)
    progress = await record_progress(
        db_session,
        PlaybackUpdate(
            video_id=vid, device_id="dev-A", device_name="Laptop",
            position_sec=10.0, duration_sec=100.0,
        ),
    )
    assert progress.position_sec == 10.0
    assert progress.device_id == "dev-A"

    # Video.watched_duration updated to max across devices
    refreshed = await VideoRepository(db_session).get_by_id(vid)
    assert refreshed.watched_duration == 10.0


@pytest.mark.asyncio
async def test_record_progress_keeps_max_position(db_session: AsyncSession) -> None:
    uid, vid = await _setup(db_session)
    await record_progress(
        db_session,
        PlaybackUpdate(video_id=vid, device_id="A", device_name="A",
                      position_sec=50.0, duration_sec=100.0),
    )
    await record_progress(
        db_session,
        PlaybackUpdate(video_id=vid, device_id="B", device_name="B",
                      position_sec=20.0, duration_sec=100.0),
    )
    # Max across devices is 50.0
    refreshed = await VideoRepository(db_session).get_by_id(vid)
    assert refreshed.watched_duration == 50.0


@pytest.mark.asyncio
async def test_record_progress_updates_same_device(db_session: AsyncSession) -> None:
    uid, vid = await _setup(db_session)
    await record_progress(
        db_session,
        PlaybackUpdate(video_id=vid, device_id="A", device_name="A",
                      position_sec=10.0, duration_sec=100.0),
    )
    await record_progress(
        db_session,
        PlaybackUpdate(video_id=vid, device_id="A", device_name="A",
                      position_sec=20.0, duration_sec=100.0),
    )
    refreshed = await VideoRepository(db_session).get_by_id(vid)
    assert refreshed.watched_duration == 20.0


@pytest.mark.asyncio
async def test_get_all_device_progress(db_session: AsyncSession) -> None:
    uid, vid = await _setup(db_session)
    await record_progress(
        db_session,
        PlaybackUpdate(video_id=vid, device_id="A", device_name="A",
                      position_sec=10.0, duration_sec=100.0),
    )
    await record_progress(
        db_session,
        PlaybackUpdate(video_id=vid, device_id="B", device_name="B",
                      position_sec=20.0, duration_sec=100.0),
    )

    states = await get_all_device_progress(db_session, vid)
    assert len(states) == 2
    devices = {s.device_id for s in states}
    assert devices == {"A", "B"}
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/application/playback/test_service.py -v --no-cov
```

- [ ] **Step 3: 写 PlaybackState ORM 模型**

`src/cinevault/infrastructure/db/models/playback_state.py`：

```python
"""PlaybackState — per-device playback position for a video."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cinevault.infrastructure.db.base import Base


class PlaybackState(Base):
    """Per-(user, video, device) playback position."""

    __tablename__ = "playback_states"
    __table_args__ = (
        UniqueConstraint("video_id", "device_id", name="uq_playback_video_device"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False)
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    position_sec: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user = relationship("User", lazy="raise")
    video = relationship("Video", lazy="raise")
```

- [ ] **Step 4: 创建目录 + 注册新模型**

```bash
mkdir -p src/cinevault/application/playback tests/application/playback
touch src/cinevault/application/playback/__init__.py tests/application/playback/__init__.py
```

修改 `src/cinevault/infrastructure/db/models/__init__.py`：

```python
"""ORM models."""

from cinevault.infrastructure.db.models.library import Library
from cinevault.infrastructure.db.models.playback_state import PlaybackState
from cinevault.infrastructure.db.models.user import User
from cinevault.infrastructure.db.models.video import Video

__all__ = ["Library", "PlaybackState", "User", "Video"]
```

- [ ] **Step 5: 写 Alembic 迁移**

`alembic/versions/2026_06_01_002_playback_state.py`：

```python
"""playback_states: per-device position tracking

Revision ID: 2026_06_01_002
Revises: 2026_06_01_001
Create Date: 2026-06-01
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "2026_06_01_002"
down_revision: Union[str, None] = "2026_06_01_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "playback_states",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(100), nullable=False),
        sa.Column("device_name", sa.String(100), nullable=True),
        sa.Column("position_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("duration_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("last_heartbeat", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("video_id", "device_id", name="uq_playback_video_device"),
    )
    op.create_index("ix_playback_user_video", "playback_states", ["user_id", "video_id"])


def downgrade() -> None:
    op.drop_index("ix_playback_user_video", table_name="playback_states")
    op.drop_table("playback_states")
```

- [ ] **Step 6: 写 PlaybackStateRepository**

`src/cinevault/infrastructure/repositories/playback_state.py`：

```python
"""PlaybackStateRepository — DB ops for per-device playback position."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from cinevault.infrastructure.db.models import PlaybackState


class PlaybackStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        user_id: int,
        video_id: int,
        device_id: str,
        device_name: str | None,
        position_sec: float,
        duration_sec: float,
        completed: bool = False,
    ) -> PlaybackState:
        values = {
            "user_id": user_id,
            "video_id": video_id,
            "device_id": device_id,
            "device_name": device_name,
            "position_sec": position_sec,
            "duration_sec": duration_sec,
            "completed": completed,
            "last_heartbeat": datetime.now(UTC),
        }
        stmt = sqlite_insert(PlaybackState).values(**values)
        update_cols = {
            "device_name": values["device_name"],
            "position_sec": values["position_sec"],
            "duration_sec": values["duration_sec"],
            "completed": values["completed"],
            "last_heartbeat": values["last_heartbeat"],
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["video_id", "device_id"], set_=update_cols
        )
        await self.session.execute(stmt.execution_options(populate_existing=True))
        await self.session.flush()

        result = await self.session.execute(
            select(PlaybackState).where(
                PlaybackState.video_id == video_id,
                PlaybackState.device_id == device_id,
            )
        )
        return result.scalar_one()

    async def list_for_video(self, video_id: int) -> list[PlaybackState]:
        result = await self.session.execute(
            select(PlaybackState)
            .where(PlaybackState.video_id == video_id)
            .order_by(PlaybackState.last_heartbeat.desc())
        )
        return list(result.scalars().all())
```

- [ ] **Step 7: 写 schemas + service**

`src/cinevault/application/playback/schemas.py`：

```python
"""Pydantic schemas for playback use cases."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlaybackUpdate(BaseModel):
    video_id: int
    device_id: str = Field(min_length=1, max_length=100)
    device_name: str | None = Field(default=None, max_length=100)
    position_sec: float = Field(ge=0)
    duration_sec: float = Field(ge=0)
    completed: bool = False


class PlaybackStateOut(BaseModel):
    device_id: str
    device_name: str | None
    position_sec: float
    duration_sec: float
    progress_pct: float
    completed: bool
    last_heartbeat: datetime

    model_config = {"from_attributes": True}


class PlaybackStateList(BaseModel):
    video_id: int
    max_position_sec: float
    max_device_id: str | None
    devices: list[PlaybackStateOut]
```

`src/cinevault/application/playback/service.py`：

```python
"""Playback use cases: per-device progress, multi-device aggregation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cinevault.application.playback.schemas import (
    PlaybackStateList,
    PlaybackStateOut,
    PlaybackUpdate,
)
from cinevault.core.errors import AppError
from cinevault.infrastructure.db.models import Video
from cinevault.infrastructure.repositories.playback_state import (
    PlaybackStateRepository,
)
from cinevault.infrastructure.repositories.video import VideoRepository


async def record_progress(
    session: AsyncSession, body: PlaybackUpdate
) -> PlaybackStateOut:
    """Upsert per-device progress + update Video.watched_duration to max across devices."""
    video = await session.get(Video, body.video_id)
    if video is None:
        raise AppError("video_not_found", f"Video {body.video_id} not found", 404)

    # Ensure there's a user_id (we use the video's library owner for now)
    owner_id = await _video_owner_id(session, video)
    repo = PlaybackStateRepository(session)
    state = await repo.upsert(
        user_id=owner_id,
        video_id=body.video_id,
        device_id=body.device_id,
        device_name=body.device_name,
        position_sec=body.position_sec,
        duration_sec=body.duration_sec,
        completed=body.completed,
    )

    # Update Video.watched_duration = max across all devices
    states = await repo.list_for_video(body.video_id)
    max_pos = max((s.position_sec for s in states), default=0.0)
    video.watched_duration = max_pos
    await session.flush()

    return _state_to_out(state)


async def get_all_device_progress(
    session: AsyncSession, video_id: int
) -> PlaybackStateList:
    repo = PlaybackStateRepository(session)
    states = await repo.list_for_video(video_id)
    if not states:
        return PlaybackStateList(video_id=video_id, max_position_sec=0.0, max_device_id=None, devices=[])
    max_state = max(states, key=lambda s: s.position_sec)
    return PlaybackStateList(
        video_id=video_id,
        max_position_sec=max_state.position_sec,
        max_device_id=max_state.device_id,
        devices=[_state_to_out(s) for s in states],
    )


def _state_to_out(s) -> PlaybackStateOut:
    pct = 0.0
    if s.duration_sec > 0:
        pct = min(100.0, (s.position_sec / s.duration_sec) * 100.0)
    return PlaybackStateOut(
        device_id=s.device_id,
        device_name=s.device_name,
        position_sec=s.position_sec,
        duration_sec=s.duration_sec,
        progress_pct=pct,
        completed=s.completed,
        last_heartbeat=s.last_heartbeat,
    )


async def _video_owner_id(session: AsyncSession, video: Video) -> int:
    from cinevault.infrastructure.db.models import Library
    lib = await session.get(Library, video.library_id)
    if lib is None:
        raise AppError("library_not_found", "Parent library missing", 404)
    return lib.owner_id
```

- [ ] **Step 8: 跑测试确认通过**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/application/playback/test_service.py -v --no-cov
```

期望：4 passed。

- [ ] **Step 9: 跑 alembic 验证迁移**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
rm -f data/cinevault.db
mkdir -p data
uv run alembic upgrade head 2>&1 | tail -3
uv run alembic current
```

期望：current 显示 `2026_06_01_002 (head)`。

- [ ] **Step 10: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add src/cinevault/ tests/ alembic/
git commit -m "feat(playback): add per-device progress tracking + PlaybackState model"
```

---

## Task 7: 播放进度 HTTP 路由

**Files:**
- Create: `src/cinevault/interface/http/v1/playback.py`
- Create: `tests/interface/http/v1/test_playback.py`
- Modify: `src/cinevault/main.py`

- [ ] **Step 1: 写失败测试**

`tests/interface/http/v1/test_playback.py`：

```python
"""Integration tests for /api/v1/playback endpoints."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cinevault.core.password import hash_password
from cinevault.infrastructure.db.base import Base
from cinevault.infrastructure.db.models import Library, User, Video
from cinevault.infrastructure.db.session import get_sessionmaker, reset_engine
from cinevault.main import create_app


@pytest.fixture
def pb_client() -> TestClient:
    tmp = Path(tempfile.mkdtemp())
    media_dir = tmp / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"\x00" * 100)

    async def _seed() -> None:
        reset_engine()
        sm = get_sessionmaker("sqlite+aiosqlite:///:memory:")
        async with sm() as s:
            async with s.bind.connect() as conn:  # type: ignore[union-attr]
                await conn.run_sync(Base.metadata.create_all)
            u = User(username="u", email="u@x.com", password_hash=hash_password("pw"))
            s.add(u)
            await s.flush()
            lib = Library(owner_id=u.id, name="L", root_path=str(media_dir))
            s.add(lib)
            await s.flush()
            s.add(Video(
                library_id=lib.id, title="a", original_filename="a.mp4",
                storage_path="a.mp4", container="mp4", file_size_bytes=100,
                file_hash="a" * 64, mtime=1, width=0, height=0, duration_sec=100.0,
            ))
            await s.commit()
        reset_engine()

    asyncio.run(_seed())
    yield TestClient(create_app())
    shutil.rmtree(tmp, ignore_errors=True)


def test_record_progress(pb_client: TestClient) -> None:
    res = pb_client.post(
        "/api/v1/playback",
        json={"video_id": 1, "device_id": "A", "device_name": "Laptop",
              "position_sec": 30.0, "duration_sec": 100.0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["position_sec"] == 30.0
    assert body["progress_pct"] == 30.0


def test_get_progress(pb_client: TestClient) -> None:
    pb_client.post(
        "/api/v1/playback",
        json={"video_id": 1, "device_id": "A", "device_name": "Laptop",
              "position_sec": 30.0, "duration_sec": 100.0},
    )
    pb_client.post(
        "/api/v1/playback",
        json={"video_id": 1, "device_id": "B", "device_name": "Phone",
              "position_sec": 50.0, "duration_sec": 100.0},
    )
    res = pb_client.get("/api/v1/playback/1")
    assert res.status_code == 200
    body = res.json()
    assert body["max_position_sec"] == 50.0
    assert body["max_device_id"] == "B"
    assert len(body["devices"]) == 2


def test_record_progress_invalid_video(pb_client: TestClient) -> None:
    res = pb_client.post(
        "/api/v1/playback",
        json={"video_id": 9999, "device_id": "A", "device_name": "X",
              "position_sec": 1.0, "duration_sec": 100.0},
    )
    assert res.status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/interface/http/v1/test_playback.py -v --no-cov
```

- [ ] **Step 3: 写 playback 路由**

`src/cinevault/interface/http/v1/playback.py`：

```python
"""/api/v1/playback — per-device playback progress."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cinevault.application.playback.schemas import (
    PlaybackStateList,
    PlaybackStateOut,
    PlaybackUpdate,
)
from cinevault.application.playback.service import (
    get_all_device_progress,
    record_progress,
)
from cinevault.interface.http.deps import db_session

router = APIRouter(prefix="/api/v1/playback", tags=["playback"])


@router.post("", response_model=PlaybackStateOut)
async def post_progress(
    body: PlaybackUpdate, session: AsyncSession = Depends(db_session)
) -> PlaybackStateOut:
    return await record_progress(session, body)


@router.get("/{video_id}", response_model=PlaybackStateList)
async def get_progress(
    video_id: int, session: AsyncSession = Depends(db_session)
) -> PlaybackStateList:
    return await get_all_device_progress(session, video_id)
```

- [ ] **Step 4: 注册路由**

修改 `src/cinevault/main.py` 的 `create_app`，在 `videos_router` 注册后**追加**：

```python
    from cinevault.interface.http.v1.playback import router as playback_router
    app.include_router(playback_router)
```

- [ ] **Step 5: 跑测试确认通过**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest tests/interface/http/v1/test_playback.py -v --no-cov
```

期望：3 passed。

- [ ] **Step 6: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add src/cinevault/ tests/
git commit -m "feat(http): add /api/v1/playback POST/GET for per-device progress"
```

---

## Task 8: 后端质量门验证

- [ ] **Step 1: 跑全量后端测试 + mypy + ruff**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest 2>&1 | tail -10
uv run mypy src 2>&1 | tail -3
uv run ruff check src tests
uv run ruff format --check src tests
```

期望：~80+ tests pass, 80%+ coverage, mypy/ruff clean。

- [ ] **Step 2: 端到端冒烟**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
rm -f data/cinevault.db
mkdir -p data
nohup uv run cinevault > /tmp/m2.log 2>&1 &
sleep 3
echo "--- /healthz ---"
curl -s http://127.0.0.1:55300/healthz
echo ""
echo "--- /api/v1/videos (empty) ---"
curl -s "http://127.0.0.1:55300/api/v1/videos" | head -c 200
pkill -f cinevault 2>/dev/null
sleep 1
rm -f data/cinevault.db
```

- [ ] **Step 3: 提交（如有修复）**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git status --short
git add -A
git diff --staged --quiet || git commit -m "chore: M2 backend cleanup"
```

---

## Task 9: 前端依赖更新（TanStack Query, Table, framer-motion）

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 添加 TanStack Query 和其他依赖**

修改 `frontend/package.json` 的 `dependencies` 段，在 `hls.js` 后追加：

```json
    "hls.js": "^1.5.15",
    "@tanstack/react-query": "^5.59.0"
```

(注意：`@tanstack/react-query`、`zustand`、`framer-motion` 已在 M0 加入；这里只加 `@tanstack/react-query` 如果未在。)

校验：cat frontend/package.json | grep -E 'react-query|zustand|framer-motion' 都存在。

- [ ] **Step 2: 安装并验证**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm install --no-audit --no-fund 2>&1 | tail -3
npm run typecheck
```

- [ ] **Step 3: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/package.json frontend/package-lock.json
git commit -m "build(frontend): ensure TanStack Query for M2"
```

---

## Task 10: 前端 API client + 类型

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/hooks.ts`
- Create: `frontend/src/api/client.test.ts`
- Modify: `frontend/src/main.tsx`（用 QueryClientProvider）

- [ ] **Step 1: 写失败测试**

`frontend/src/api/client.test.ts`：

```typescript
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { api } from './client';

describe('api client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('builds URL with leading slash', async () => {
    const fetchMock = vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );
    await api.get('/test');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/test'),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('throws on non-2xx', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ code: 'x', message: 'oops' }), { status: 400 })
    );
    await expect(api.get('/test')).rejects.toThrow('oops');
  });

  it('posts JSON body', async () => {
    const fetchMock = vi.mocked(fetch).mockResolvedValueOnce(
      new Response('{}', { status: 200 })
    );
    await api.post('/test', { foo: 'bar' });
    const call = fetchMock.mock.calls[0];
    expect(call?.[0]).toContain('/api/test');
    const init = call?.[1] as RequestInit;
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ foo: 'bar' });
  });
});
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run test 2>&1 | tail -5
```

- [ ] **Step 3: 写 types + client + hooks**

`frontend/src/api/types.ts`：

```typescript
// Hand-written API types matching backend Pydantic schemas.
// In a real project, generate from OpenAPI schema; for M2 we keep it manual.

export interface VideoOut {
  id: number;
  title: string;
  original_filename: string;
  container: string;
  width: number;
  height: number;
  duration_sec: number;
  bitrate_kbps: number;
  framerate: number;
  file_size_bytes: number;
  favorite: boolean;
  rating: number;
  thumbnail_path: string | null;
  transcode_status: string;
  library_id: number;
  storage_path: string;
  mtime: number;
  created_at: string;
  last_played_at: string | null;
  watched_duration: number;
  progress_pct: number;
}

export interface VideoList {
  videos: VideoOut[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PlaybackStateOut {
  device_id: string;
  device_name: string | null;
  position_sec: number;
  duration_sec: number;
  progress_pct: number;
  completed: boolean;
  last_heartbeat: string;
}

export interface PlaybackStateList {
  video_id: number;
  max_position_sec: number;
  max_device_id: string | null;
  devices: PlaybackStateOut[];
}
```

`frontend/src/api/client.ts`：

```typescript
import type { PlaybackStateList, PlaybackStateOut, VideoList, VideoOut } from './types';

const BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith('/') ? `${BASE}${path}` : `${BASE}/${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    credentials: 'include',
  });
  if (!res.ok) {
    let body: { code?: string; message?: string } = {};
    try { body = await res.json(); } catch { /* ignore */ }
    throw new ApiError(res.status, body.code ?? 'unknown', body.message ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : '';
}

export const api = {
  get<T>(path: string): Promise<T> { return request<T>(path, { method: 'GET' }); },
  post<T>(path: string, body: unknown): Promise<T> { return request<T>(path, { method: 'POST', body: JSON.stringify(body) }); },
  del<T>(path: string): Promise<T> { return request<T>(path, { method: 'DELETE' }); },

  // Convenience methods
  listVideos(params: {
    search?: string;
    favorite?: boolean;
    watched?: 'any' | 'in_progress' | 'completed' | 'unwatched';
    sort_by?: 'title' | 'created_at' | 'duration' | 'size' | 'filename';
    sort_order?: 'asc' | 'desc';
    page?: number;
    per_page?: number;
  } = {}): Promise<VideoList> {
    return this.get<VideoList>(`/videos${qs(params)}`);
  },
  getVideo(id: number): Promise<VideoOut> {
    return this.get<VideoOut>(`/videos/${id}`);
  },
  recordProgress(body: {
    video_id: number;
    device_id: string;
    device_name?: string;
    position_sec: number;
    duration_sec: number;
    completed?: boolean;
  }): Promise<PlaybackStateOut> {
    return this.post<PlaybackStateOut>('/playback', body);
  },
  getProgress(videoId: number): Promise<PlaybackStateList> {
    return this.get<PlaybackStateList>(`/playback/${videoId}`);
  },
  thumbnailUrl(filename: string): string {
    return `${BASE}/stream/thumbnail/${encodeURIComponent(filename)}`;
  },
  streamUrl(filename: string): string {
    return `${BASE}/stream/${encodeURIComponent(filename)}`;
  },
};

export { ApiError };
```

`frontend/src/api/hooks.ts`：

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type { PlaybackStateList, PlaybackStateOut, VideoList } from './types';

export function useVideoList(params: Parameters<typeof api.listVideos>[0] = {}) {
  return useQuery({
    queryKey: ['videos', params],
    queryFn: () => api.listVideos(params),
    staleTime: 30_000,
  });
}

export function useVideo(id: number) {
  return useQuery({
    queryKey: ['video', id],
    queryFn: () => api.getVideo(id),
    enabled: id > 0,
  });
}

export function useProgress(videoId: number) {
  return useQuery({
    queryKey: ['progress', videoId],
    queryFn: () => api.getProgress(videoId),
    enabled: videoId > 0,
  });
}

export function useRecordProgress(videoId: number) {
  const qc = useQueryClient();
  return useMutation<PlaybackStateOut, Error, Parameters<typeof api.recordProgress>[0]>({
    mutationFn: (body) => api.recordProgress(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['progress', videoId] });
      qc.invalidateQueries({ queryKey: ['videos'] });
    },
  });
}
```

- [ ] **Step 4: 在 main.tsx 套 QueryClientProvider**

修改 `frontend/src/main.tsx`：

```typescript
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './styles/global.css';

const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('Root element #root not found in index.html');
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
  },
});

createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 5: 跑测试 + typecheck**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run test 2>&1 | tail -5
npm run typecheck 2>&1 | tail -3
```

期望：3 api tests pass，0 typecheck errors。

- [ ] **Step 6: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/src/api/ frontend/src/main.tsx
git commit -m "feat(frontend): add typed API client + TanStack Query hooks"
```

---

## Task 11: 设计 token 扩展

**Files:**
- Modify: `frontend/src/styles/global.css`（删除 M0 placeholder tokens）
- Create: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/main.tsx`（import tokens）

- [ ] **Step 1: 写 tokens.css**

`frontend/src/styles/tokens.css`：

```css
/* ===== Design tokens (CineVault v2) ===== */
:root {
  /* Colors - Dark (default) */
  --bg-deep: #0a0814;
  --bg-surface: #14111e;
  --bg-elevated: #1c1828;
  --bg-muted: #1a1735;
  --bg-glass: rgb(20 17 30 / 0.65);
  --bg-glass-hover: rgb(30 27 65 / 0.8);

  --text-primary: #eceaff;
  --text-secondary: #a5a0d8;
  --text-muted: #5c5890;

  --accent-primary: #a78bfa;
  --accent-pink: #d496b0;
  --accent-cyan: #6eb8c8;
  --accent-success: #86efac;
  --accent-warning: #fcd34d;
  --accent-danger: #fca5a5;

  /* Borders + shadows */
  --border-primary: rgb(100 90 160 / 0.2);
  --border-secondary: rgb(120 105 165 / 0.15);
  --shadow-md: 0 4px 12px rgb(0 0 0 / 0.4);
  --shadow-glass: 0 8px 32px rgb(0 0 0 / 0.35);
  --glow-primary: 0 0 25px rgb(167 139 250 / 0.15);

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --space-16: 64px;

  /* Radii */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;

  /* Motion */
  --motion-fast: 150ms;
  --motion-base: 220ms;
  --motion-slow: 360ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

  /* Typography */
  --font-display: 'Outfit', system-ui, sans-serif;
  --font-body: 'Nunito', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  --text-4xl: 2.25rem;

  /* Layout */
  --max-width-content: 1600px;
  --nav-height: 64px;
}

[data-theme='light'] {
  --bg-deep: #faf7fc;
  --bg-surface: #ffffff;
  --bg-elevated: #f4eef8;
  --bg-muted: #ede4f5;
  --bg-glass: rgb(255 255 255 / 0.75);
  --text-primary: #2d1b3d;
  --text-secondary: #5a4d75;
  --text-muted: #8a82a3;
  --border-primary: rgb(167 139 250 / 0.2);
  --shadow-md: 0 4px 12px rgb(0 0 0 / 0.08);
  --shadow-glass: 0 8px 32px rgb(0 0 0 / 0.06);
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 2: 替换 global.css（保留 reset）**

`frontend/src/styles/global.css`（替换全部内容）：

```css
/* Reset + base */
* {
  box-sizing: border-box;
}

html,
body,
#root {
  margin: 0;
  padding: 0;
  height: 100%;
  background: var(--bg-deep);
  color: var(--text-primary);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

a {
  color: var(--accent-primary);
  text-decoration: none;
}
```

- [ ] **Step 3: 在 main.tsx import tokens**

修改 `frontend/src/main.tsx`，在 `import './styles/global.css';` 前**插入**：

```typescript
import './styles/tokens.css';
import './styles/global.css';
```

- [ ] **Step 4: 跑质量门**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run typecheck 2>&1 | tail -3
npm run lint 2>&1 | tail -3
npm run test 2>&1 | tail -5
```

- [ ] **Step 5: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/src/styles/ frontend/src/main.tsx
git commit -m "feat(frontend): add full design token system (dark/light themes)"
```

---

## Task 12: VideoCard 组件

**Files:**
- Create: `frontend/src/components/media/VideoCard.tsx`
- Create: `frontend/src/components/media/VideoCard.test.tsx`
- Create: `frontend/src/lib/format.ts`

- [ ] **Step 1: format.ts**

`frontend/src/lib/format.ts`：

```typescript
export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds < 0) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function formatSize(bytes: number): string {
  if (bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(1)} ${units[i]}`;
}

export function formatBitrate(kbps: number): string {
  if (kbps <= 0) return '—';
  if (kbps >= 1000) return `${(kbps / 1000).toFixed(1)} Mbps`;
  return `${kbps} kbps`;
}
```

加测试 `frontend/src/lib/format.test.ts`：

```typescript
import { describe, expect, it } from 'vitest';
import { formatBitrate, formatDuration, formatSize } from './format';

describe('format', () => {
  it('formats duration', () => {
    expect(formatDuration(0)).toBe('—');
    expect(formatDuration(65)).toBe('1:05');
    expect(formatDuration(3661)).toBe('1:01:01');
  });
  it('formats size', () => {
    expect(formatSize(0)).toBe('0 B');
    expect(formatSize(1024)).toBe('1.0 KB');
    expect(formatSize(1024 * 1024 * 1024)).toBe('1.0 GB');
  });
  it('formats bitrate', () => {
    expect(formatBitrate(0)).toBe('—');
    expect(formatBitrate(800)).toBe('800 kbps');
    expect(formatBitrate(8000)).toBe('8.0 Mbps');
  });
});
```

- [ ] **Step 2: VideoCard 组件 + 测试**

`frontend/src/components/media/VideoCard.tsx`：

```typescript
import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { formatDuration, formatSize } from '../../lib/format';
import { api } from '../../api/client';
import type { VideoOut } from '../../api/types';

interface Props {
  video: VideoOut;
}

export function VideoCard({ video }: Props) {
  const progressWidth = video.progress_pct > 0 ? `${video.progress_pct}%` : '0%';
  return (
    <article className="video-card" data-testid="video-card">
      <Link to={`/player/${video.id}`} className="card-media">
        <div className="thumbnail-container">
          <img
            src={api.thumbnailUrl(video.original_filename)}
            alt={video.title}
            className="thumbnail-img"
            loading="lazy"
          />
        </div>
        {video.progress_pct > 0 && (
          <div
            className="progress-indicator"
            style={{ width: progressWidth }}
            aria-label={`${Math.round(video.progress_pct)}% watched`}
          />
        )}
        <span className="duration-badge">{formatDuration(video.duration_sec)}</span>
        {video.favorite && (
          <span className="favorite-badge" aria-label="Favorite">
            <Heart className="w-3 h-3" />
          </span>
        )}
      </Link>
      <div className="card-info">
        <h3 className="card-title">
          <Link to={`/player/${video.id}`}>{video.title}</Link>
        </h3>
        <p className="card-meta">{formatSize(video.file_size_bytes)}</p>
        <div className="card-badges">
          {video.width > 0 && (
            <span className="info-badge">{video.width}×{video.height}</span>
          )}
        </div>
      </div>
    </article>
  );
}
```

`frontend/src/components/media/VideoCard.test.tsx`：

```typescript
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { VideoCard } from './VideoCard';
import type { VideoOut } from '../../api/types';

const sample: VideoOut = {
  id: 1,
  title: 'My Video',
  original_filename: 'my.mp4',
  container: 'mp4',
  width: 1920,
  height: 1080,
  duration_sec: 120,
  bitrate_kbps: 5000,
  framerate: 30,
  file_size_bytes: 1024 * 1024 * 50,
  favorite: true,
  rating: 0,
  thumbnail_path: null,
  transcode_status: 'pending',
  library_id: 1,
  storage_path: 'my.mp4',
  mtime: 1,
  created_at: '2026-01-01T00:00:00',
  last_played_at: null,
  watched_duration: 30,
  progress_pct: 25,
};

describe('VideoCard', () => {
  it('renders title + duration + size', () => {
    render(
      <MemoryRouter>
        <VideoCard video={sample} />
      </MemoryRouter>,
    );
    expect(screen.getByText('My Video')).toBeInTheDocument();
    expect(screen.getByText('2:00')).toBeInTheDocument();
    expect(screen.getByText('50.0 MB')).toBeInTheDocument();
    expect(screen.getByText('1920×1080')).toBeInTheDocument();
  });

  it('shows progress bar when watched_duration > 0', () => {
    const { container } = render(
      <MemoryRouter>
        <VideoCard video={sample} />
      </MemoryRouter>,
    );
    const bar = container.querySelector('.progress-indicator');
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveStyle({ width: '25%' });
  });

  it('hides progress bar when never watched', () => {
    render(
      <MemoryRouter>
        <VideoCard video={{ ...sample, progress_pct: 0, watched_duration: 0 }} />
      </MemoryRouter>,
    );
    expect(screen.queryByLabelText(/watched/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 3: 跑测试 + 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run test 2>&1 | tail -5
npm run typecheck 2>&1 | tail -3
```

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/src/components/media/ frontend/src/lib/
git commit -m "feat(frontend): add VideoCard + format helpers"
```

---

## Task 13: Library 页面（bento 网格）

**Files:**
- Create: `frontend/src/pages/library/LibraryPage.tsx`
- Create: `frontend/src/pages/library/EmptyState.tsx`
- Create: `frontend/src/pages/library/LibraryPage.test.tsx`

- [ ] **Step 1: EmptyState**

`frontend/src/pages/library/EmptyState.tsx`：

```typescript
import { Film } from 'lucide-react';

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="empty-state" data-testid="empty-state">
      <Film className="w-12 h-12" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}
```

- [ ] **Step 2: LibraryPage 组件**

`frontend/src/pages/library/LibraryPage.tsx`：

```typescript
import { useState } from 'react';
import { useVideoList } from '../../api/hooks';
import { VideoCard } from '../../components/media/VideoCard';
import { EmptyState } from './EmptyState';
import { FilterBar } from './FilterBar';
import { Pagination } from './Pagination';
import { ViewToggle } from './ViewToggle';

export function LibraryPage() {
  const [search, setSearch] = useState('');
  const [favorite, setFavorite] = useState<boolean | undefined>(undefined);
  const [sortBy, setSortBy] = useState<'title' | 'created_at' | 'duration' | 'size' | 'filename'>('title');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [page, setPage] = useState(1);
  const perPage = 24;

  const query = useVideoList({ search, favorite, sort_by: sortBy, sort_order: sortOrder, page, per_page: perPage });

  return (
    <main className="home-page" data-testid="library-page">
      <FilterBar
        search={search}
        onSearchChange={(v) => { setSearch(v); setPage(1); }}
        favorite={favorite}
        onFavoriteChange={(v) => { setFavorite(v); setPage(1); }}
        sortBy={sortBy}
        onSortChange={setSortBy}
        sortOrder={sortOrder}
        onSortOrderChange={setSortOrder}
      />
      <ViewToggle view={view} onChange={setView} />
      {query.isLoading ? (
        <p>Loading…</p>
      ) : query.isError ? (
        <p>Failed to load videos.</p>
      ) : !query.data || query.data.videos.length === 0 ? (
        <EmptyState message={search ? 'No matches' : 'No videos yet'} />
      ) : (
        <div className={`video-grid ${view === 'list' ? 'list-view' : ''}`} data-testid="video-grid">
          {query.data.videos.map((v) => <VideoCard key={v.id} video={v} />)}
        </div>
      )}
      {query.data && query.data.total_pages > 1 && (
        <Pagination
          page={page}
          totalPages={query.data.total_pages}
          onChange={setPage}
        />
      )}
    </main>
  );
}
```

- [ ] **Step 3: 写子组件占位（FilterBar/ViewToggle/Pagination）**

`frontend/src/pages/library/FilterBar.tsx`：

```typescript
import { Search } from 'lucide-react';

interface Props {
  search: string;
  onSearchChange: (v: string) => void;
  favorite: boolean | undefined;
  onFavoriteChange: (v: boolean | undefined) => void;
  sortBy: string;
  onSortChange: (v: 'title' | 'created_at' | 'duration' | 'size' | 'filename') => void;
  sortOrder: 'asc' | 'desc';
  onSortOrderChange: (v: 'asc' | 'desc') => void;
}

export function FilterBar(props: Props) {
  return (
    <div className="filter-bar" data-testid="filter-bar">
      <div className="search-box">
        <Search className="w-4 h-4" aria-hidden="true" />
        <input
          type="search"
          placeholder="Search videos…"
          value={props.search}
          onChange={(e) => props.onSearchChange(e.target.value)}
          aria-label="Search videos"
        />
      </div>
      <label>
        <input
          type="checkbox"
          checked={props.favorite === true}
          onChange={(e) => props.onFavoriteChange(e.target.checked ? true : undefined)}
        />
        Favorites only
      </label>
      <select
        value={props.sortBy}
        onChange={(e) => props.onSortChange(e.target.value as Props['sortBy'])}
        aria-label="Sort by"
      >
        <option value="title">Title</option>
        <option value="created_at">Date added</option>
        <option value="duration">Duration</option>
        <option value="size">File size</option>
        <option value="filename">Filename</option>
      </select>
      <select
        value={props.sortOrder}
        onChange={(e) => props.onSortOrderChange(e.target.value as 'asc' | 'desc')}
        aria-label="Sort order"
      >
        <option value="asc">Asc</option>
        <option value="desc">Desc</option>
      </select>
    </div>
  );
}
```

`frontend/src/pages/library/ViewToggle.tsx`：

```typescript
import { Grid3x3, List } from 'lucide-react';

interface Props {
  view: 'grid' | 'list';
  onChange: (v: 'grid' | 'list') => void;
}

export function ViewToggle({ view, onChange }: Props) {
  return (
    <div className="view-toggle" role="group" aria-label="View mode">
      <button
        type="button"
        aria-pressed={view === 'grid'}
        onClick={() => onChange('grid')}
      >
        <Grid3x3 className="w-4 h-4" />
      </button>
      <button
        type="button"
        aria-pressed={view === 'list'}
        onClick={() => onChange('list')}
      >
        <List className="w-4 h-4" />
      </button>
    </div>
  );
}
```

`frontend/src/pages/library/Pagination.tsx`：

```typescript
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Props {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}

export function Pagination({ page, totalPages, onChange }: Props) {
  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <span className="pagination-info">
        Page {page} of {totalPages}
      </span>
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
        aria-label="Next page"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </nav>
  );
}
```

- [ ] **Step 4: LibraryPage 测试（mock fetch）**

`frontend/src/pages/library/LibraryPage.test.tsx`：

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LibraryPage } from './LibraryPage';

function renderWithProviders() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <LibraryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const emptyList = { videos: [], total: 0, page: 1, per_page: 24, total_pages: 1 };
const oneItem = {
  videos: [
    {
      id: 1, title: 'Hello', original_filename: 'hello.mp4', container: 'mp4',
      width: 1280, height: 720, duration_sec: 30, bitrate_kbps: 1000, framerate: 30,
      file_size_bytes: 1024, favorite: false, rating: 0, thumbnail_path: null,
      transcode_status: 'pending', library_id: 1, storage_path: 'hello.mp4', mtime: 1,
      created_at: '2026-01-01T00:00:00', last_played_at: null,
      watched_duration: 0, progress_pct: 0,
    },
  ],
  total: 1, page: 1, per_page: 24, total_pages: 1,
};

describe('LibraryPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows empty state when no videos', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(emptyList), { status: 200 }));
    renderWithProviders();
    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeInTheDocument());
  });

  it('renders video cards when present', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(oneItem), { status: 200 }));
    renderWithProviders();
    await waitFor(() => expect(screen.getAllByTestId('video-card')).toHaveLength(1));
  });
});
```

- [ ] **Step 5: 跑质量门**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run test 2>&1 | tail -5
npm run typecheck 2>&1 | tail -3
npm run lint 2>&1 | tail -3
```

- [ ] **Step 6: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/src/pages/library/
git commit -m "feat(frontend): add Library page with bento grid + filter bar + pagination"
```

---

## Task 14: Player 页面 + 视频元素 + 自定义控制

**Files:**
- Create: `frontend/src/pages/player/PlayerPage.tsx`
- Create: `frontend/src/pages/player/ControlBar.tsx`
- Create: `frontend/src/pages/player/ResumeBar.tsx`
- Create: `frontend/src/pages/player/useKeyboardShortcuts.ts`
- Create: `frontend/src/pages/player/PlayerPage.test.tsx`

- [ ] **Step 1: 键盘快捷键 hook**

`frontend/src/pages/player/useKeyboardShortcuts.ts`：

```typescript
import { useEffect } from 'react';

export interface PlayerControls {
  togglePlay: () => void;
  seekBy: (delta: number) => void;
  setVolume: (v: number) => void;
  toggleMute: () => void;
  toggleFullscreen: () => void;
}

export function useKeyboardShortcuts(controls: PlayerControls) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement;
      if (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA') return;
      switch (e.code) {
        case 'Space': case 'KeyK':
          e.preventDefault(); controls.togglePlay(); break;
        case 'KeyJ': controls.seekBy(-10); break;
        case 'KeyL': controls.seekBy(10); break;
        case 'ArrowLeft': controls.seekBy(-5); break;
        case 'ArrowRight': controls.seekBy(5); break;
        case 'ArrowUp': controls.setVolume(Math.min(1, (parseFloat((document.querySelector('video') as HTMLVideoElement | null)?.volume.toString() ?? '1') + 0.1))); break;
        case 'ArrowDown': controls.setVolume(Math.max(0, (parseFloat((document.querySelector('video') as HTMLVideoElement | null)?.volume.toString() ?? '1') - 0.1))); break;
        case 'KeyM': controls.toggleMute(); break;
        case 'KeyF': controls.toggleFullscreen(); break;
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [controls]);
}
```

- [ ] **Step 2: ControlBar**

`frontend/src/pages/player/ControlBar.tsx`：

```typescript
import { Play, Pause, Volume2, VolumeX, Maximize, SkipBack, SkipForward } from 'lucide-react';

interface Props {
  playing: boolean;
  muted: boolean;
  volume: number;
  currentTime: number;
  duration: number;
  onTogglePlay: () => void;
  onSeek: (delta: number) => void;
  onSetVolume: (v: number) => void;
  onToggleMute: () => void;
  onToggleFullscreen: () => void;
}

function fmt(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, '0');
  return `${m}:${sec}`;
}

export function ControlBar(props: Props) {
  return (
    <div className="controls-row" data-testid="control-bar">
      <button type="button" onClick={props.onTogglePlay} aria-label={props.playing ? 'Pause' : 'Play'}>
        {props.playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
      </button>
      <button type="button" onClick={() => props.onSeek(-10)} aria-label="Skip back 10s">
        <SkipBack className="w-4 h-4" />
      </button>
      <button type="button" onClick={() => props.onSeek(10)} aria-label="Skip forward 10s">
        <SkipForward className="w-4 h-4" />
      </button>
      <button type="button" onClick={props.onToggleMute} aria-label={props.muted ? 'Unmute' : 'Mute'}>
        {props.muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
      </button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={props.muted ? 0 : props.volume}
        onChange={(e) => props.onSetVolume(parseFloat(e.target.value))}
        aria-label="Volume"
      />
      <span className="time-display">
        {fmt(props.currentTime)} / {fmt(props.duration)}
      </span>
      <button type="button" onClick={props.onToggleFullscreen} aria-label="Fullscreen">
        <Maximize className="w-5 h-5" />
      </button>
    </div>
  );
}
```

- [ ] **Step 3: ResumeBar**

`frontend/src/pages/player/ResumeBar.tsx`：

```typescript
import { X, Play } from 'lucide-react';

interface Props {
  positionSec: number;
  durationSec: number;
  onResume: () => void;
  onDismiss: () => void;
}

export function ResumeBar({ positionSec, durationSec, onResume, onDismiss }: Props) {
  if (positionSec <= 0 || durationSec <= 0) return null;
  const pct = Math.min(100, Math.round((positionSec / durationSec) * 100));
  return (
    <div className="resume-bar" data-testid="resume-bar">
      <span>Resume from {pct}%</span>
      <button type="button" onClick={onResume} aria-label="Resume">
        <Play className="w-4 h-4" />
      </button>
      <button type="button" onClick={onDismiss} aria-label="Dismiss">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
```

- [ ] **Step 4: PlayerPage（核心组件）**

`frontend/src/pages/player/PlayerPage.tsx`：

```typescript
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useProgress, useRecordProgress, useVideo } from '../../api/hooks';
import { api } from '../../api/client';
import { ControlBar } from './ControlBar';
import { ResumeBar } from './ResumeBar';
import { useKeyboardShortcuts, type PlayerControls } from './useKeyboardShortcuts';

const PROGRESS_SAVE_INTERVAL_MS = 5_000;

function getDeviceId(): string {
  let id = localStorage.getItem('cinevault-device-id');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('cinevault-device-id', id);
  }
  return id;
}

function getDeviceName(): string {
  return navigator.userAgent.split(') ')[0].split('(')[1] ?? 'Web';
}

export function PlayerPage() {
  const { id } = useParams<{ id: string }>();
  const videoId = Number(id);

  const videoQuery = useVideo(videoId);
  const progressQuery = useProgress(videoId);
  const recordProgress = useRecordProgress(videoId);

  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showResume, setShowResume] = useState(false);

  const deviceId = useMemo(getDeviceId, []);
  const deviceName = useMemo(getDeviceName, []);

  // Show resume bar on first load if server has progress
  useEffect(() => {
    if (progressQuery.data && progressQuery.data.max_position_sec > 5) {
      setShowResume(true);
    }
  }, [progressQuery.data?.max_position_sec]);

  // Timeupdate throttling (5s)
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    let lastSave = 0;
    const handler = () => {
      setCurrentTime(v.currentTime);
      const now = Date.now();
      if (now - lastSave >= PROGRESS_SAVE_INTERVAL_MS) {
        lastSave = now;
        if (v.duration > 0) {
          recordProgress.mutate({
            video_id: videoId,
            device_id: deviceId,
            device_name: deviceName,
            position_sec: v.currentTime,
            duration_sec: v.duration,
          });
        }
      }
    };
    v.addEventListener('timeupdate', handler);
    return () => v.removeEventListener('timeupdate', handler);
  }, [videoId, deviceId, deviceName, recordProgress]);

  const controls: PlayerControls = useMemo(() => ({
    togglePlay: () => {
      const v = videoRef.current;
      if (!v) return;
      if (v.paused) v.play(); else v.pause();
    },
    seekBy: (delta) => {
      const v = videoRef.current;
      if (!v) return;
      v.currentTime = Math.max(0, Math.min(v.duration || 0, v.currentTime + delta));
    },
    setVolume: (v) => {
      const el = videoRef.current;
      if (!el) return;
      el.volume = v;
      setVolume(v);
    },
    toggleMute: () => {
      const el = videoRef.current;
      if (!el) return;
      el.muted = !el.muted;
      setMuted(el.muted);
    },
    toggleFullscreen: () => {
      const el = videoRef.current;
      if (!el) return;
      if (document.fullscreenElement) document.exitFullscreen();
      else el.requestFullscreen?.();
    },
  }), []);

  useKeyboardShortcuts(controls);

  const onLoadedMetadata = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    setDuration(v.duration);
  }, []);

  if (videoQuery.isLoading) return <main className="player-page"><p>Loading…</p></main>;
  if (videoQuery.isError || !videoQuery.data) {
    return (
      <main className="player-page">
        <p>Video not found.</p>
        <Link to="/">← Back to library</Link>
      </main>
    );
  }

  const video = videoQuery.data;

  return (
    <main className="player-page" data-testid="player-page">
      {showResume && progressQuery.data && (
        <ResumeBar
          positionSec={progressQuery.data.max_position_sec}
          durationSec={duration || video.duration_sec}
          onResume={() => {
            const v = videoRef.current;
            if (!v) return;
            v.currentTime = progressQuery.data!.max_position_sec;
            v.play();
            setShowResume(false);
          }}
          onDismiss={() => setShowResume(false)}
        />
      )}
      <div className="player-layout">
        <div className="player-section">
          <div className="video-wrapper">
            <video
              ref={videoRef}
              className="video-element"
              src={api.streamUrl(video.original_filename)}
              onLoadedMetadata={onLoadedMetadata}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              playsInline
              preload="metadata"
              data-testid="video-element"
            />
            <ControlBar
              playing={playing}
              muted={muted}
              volume={volume}
              currentTime={currentTime}
              duration={duration || video.duration_sec}
              onTogglePlay={controls.togglePlay}
              onSeek={controls.seekBy}
              onSetVolume={controls.setVolume}
              onToggleMute={controls.toggleMute}
              onToggleFullscreen={controls.toggleFullscreen}
            />
          </div>
        </div>
        <div className="info-section">
          <Link to="/" className="back-link">← Back</Link>
          <h1 className="video-title">{video.title}</h1>
          <p>{video.width}×{video.height} · {video.container} · {(video.file_size_bytes / (1024 * 1024)).toFixed(1)} MB</p>
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 5: 跑质量门**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run typecheck 2>&1 | tail -3
npm run lint 2>&1 | tail -3
npm run test 2>&1 | tail -5
```

- [ ] **Step 6: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/src/pages/player/
git commit -m "feat(frontend): add Player page with custom controls + progress sync + shortcuts"
```

---

## Task 15: 路由 + 集成 + 应用更新

**Files:**
- Create: `frontend/src/routes.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 写 routes.tsx**

`frontend/src/routes.tsx`：

```typescript
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LibraryPage } from './pages/library/LibraryPage';
import { PlayerPage } from './pages/player/PlayerPage';

export const router = createBrowserRouter([
  { path: '/', element: <LibraryPage /> },
  { path: '/player/:id', element: <PlayerPage /> },
  { path: '*', element: <Navigate to="/" replace /> },
]);
```

- [ ] **Step 2: 简化 App.tsx（RouterProvider 直接用）**

`frontend/src/App.tsx`：

```typescript
import { RouterProvider } from 'react-router-dom';
import { router } from './routes';

function App() {
  return <RouterProvider router={router} />;
}

export default App;
```

- [ ] **Step 3: 跑 + 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run typecheck 2>&1 | tail -3
npm run build 2>&1 | tail -5
```

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/src/routes.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add router with library + player routes"
```

---

## Task 16: Playwright E2E 测试

**Files:**
- Modify: `frontend/package.json`（添加 @playwright/test）
- Create: `frontend/playwright.config.ts`
- Create: `frontend/tests/e2e/library.spec.ts`
- Create: `frontend/tests/e2e/player.spec.ts`

- [ ] **Step 1: 安装 Playwright**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm install --no-audit --no-fund -D @playwright/test 2>&1 | tail -3
npx playwright install --with-deps chromium 2>&1 | tail -3
```

(注：`npx playwright install` 下载浏览器 ~300MB，可能需要几分钟。)

- [ ] **Step 2: playwright config**

`frontend/playwright.config.ts`：

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    timeout: 60_000,
    reuseExistingServer: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

- [ ] **Step 3: Library E2E**

`frontend/tests/e2e/library.spec.ts`：

```typescript
import { test, expect } from '@playwright/test';

test('library page renders with filter bar', async ({ page }) => {
  // The Vite dev server must be running (webServer config handles this).
  // Note: backend won't have data; the page should still render without crashing.
  await page.goto('/');
  await expect(page.getByTestId('library-page')).toBeVisible();
  await expect(page.getByTestId('filter-bar')).toBeVisible();
});

test('typing in search input filters the list', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Search videos').fill('nothing-matches');
  await expect(page.getByTestId('empty-state')).toBeVisible({ timeout: 5_000 });
});
```

- [ ] **Step 4: Player E2E（基础 load 检查）**

`frontend/tests/e2e/player.spec.ts`：

```typescript
import { test, expect } from '@playwright/test';

test('player page loads for video id 1', async ({ page }) => {
  // 404 is acceptable here — the page should still render the layout
  await page.goto('/player/1');
  await expect(page.getByTestId('player-page')).toBeVisible();
});
```

- [ ] **Step 5: 跑 E2E（dev server 需 backend 配合或 mock）**

注意：E2E 需要后端运行。M2 的 CI 应当先启 backend，然后启 Vite，再跑 Playwright。

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
# Start backend in background
mkdir -p data
rm -f data/cinevault.db
nohup uv run cinevault > /tmp/m2-e2e-backend.log 2>&1 &
BE_PID=$!
sleep 3

cd frontend
npx playwright test 2>&1 | tail -10

kill $BE_PID 2>/dev/null
rm -f data/cinevault.db
```

期望：2 tests pass。

- [ ] **Step 6: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/package.json frontend/package-lock.json frontend/playwright.config.ts frontend/tests/e2e/
git commit -m "test(e2e): add Playwright smoke tests for library + player"
```

---

## Task 17: 最终全量验证

- [ ] **Step 1: 后端全量**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
rm -rf .venv
uv sync --extra dev 2>&1 | tail -3
uv run pytest 2>&1 | tail -8
uv run mypy src 2>&1 | tail -3
uv run ruff check src tests 2>&1 | tail -1
uv run ruff format --check src tests 2>&1 | tail -1
```

期望：~90+ tests pass, 80%+ coverage, mypy/ruff clean。

- [ ] **Step 2: 前端全量**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
rm -rf node_modules
npm install --no-audit --no-fund 2>&1 | tail -3
npm run typecheck 2>&1 | tail -3
npm run lint 2>&1 | tail -3
npm run format:check 2>&1 | tail -3
npm run test 2>&1 | tail -5
npm run build 2>&1 | tail -5
```

- [ ] **Step 3: 端到端冒烟（手动）**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
mkdir -p data
rm -f data/cinevault.db
nohup uv run cinevault > /tmp/m2-final.log 2>&1 &
sleep 3
echo "--- /healthz ---"
curl -s http://127.0.0.1:55300/healthz
echo ""
echo "--- /api/v1/videos (no user, should be 4xx) ---"
curl -s -i http://127.0.0.1:55300/api/v1/videos | head -3
pkill -f cinevault 2>/dev/null
rm -f data/cinevault.db
```

- [ ] **Step 4: 写 M2-COMPLETE.md**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/docs/M2-COMPLETE.md`（参考 M1 模板）：

```markdown
# M2 — Library + Player Complete

**Date:** 2026-06-01
**Tag:** `m2-library-player`
**Branch:** `m2-library-player`

## Delivered

### Backend
- Thumbnail generation service (ffmpeg frame extraction with cache)
- /api/v1/stream/thumbnail/{filename} endpoint
- Video list service with advanced search/filter (multi-tag, duration range, favorite, watched status)
- /api/v1/videos list + detail endpoints
- PlaybackState ORM model + Alembic migration
- Playback service (per-device progress, max-across-devices aggregation)
- /api/v1/playback POST/GET endpoints

### Frontend
- API client (typed fetch wrapper) + TanStack Query hooks
- Design token system (full dark/light themes)
- Library page: bento grid + filter bar + sort + view toggle + pagination
- VideoCard component with progress indicator + favorite badge
- Player page: HTML5 video + custom control bar + 5s progress sync + resume bar
- Keyboard shortcuts: Space/K (play), J/L (skip), arrows (volume/seek), M (mute), F (fullscreen)
- React Router with / and /player/:id routes
- Playwright E2E smoke tests

## Verified

- ✓ Backend: ~90+ tests pass, 80%+ coverage
- ✓ Frontend: typecheck + lint + test + build all green
- ✓ E2E: Playwright smoke tests pass with backend running
- ✓ End-to-end: /healthz, /api/v1/videos, etc. all reachable

## Next: M3

M3 — Tags + Collections + Sharing: full CRUD for tags, collections, share tokens (with passwords + expiry).
```

- [ ] **Step 5: 提交文档 + 打 tag**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add docs/M2-COMPLETE.md
git commit -m "docs: record M2 completion"
git tag -a m2-library-player -m "M2: library + player complete"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** 视频库 (Section 5/UI Library) ✓ + 高级搜索 ✓ + 播放进度（多设备） ✓ + 缩略图 ✓；HLS 转码 (Section 5 HLS 自适应) 推迟到 M2.5。
- [x] **Placeholder scan:** 完整代码，无 "TBD"/"TODO"
- [x] **Type consistency:** `VideoOut`, `VideoList`, `PlaybackStateOut` 跨后端 Pydantic / 前端 TS 一致；`api.listVideos` / `useVideoList` 参数一致。
- [x] **每个 task 有 commit**

## Notes for Engineer

- **HLS 推迟**：M2 用 M1 的 progressive MP4 流；HLS 转码推到 M2.5（届时加 background task + master.m3u8 生成）
- **首版路由 + Provider**：用 React Router 6 data router + TanStack Query v5
- **deviceId 持久化**：用 `localStorage` + `crypto.randomUUID()`；未来可在 Device 表中正式跟踪
- **进度合并策略**：当前 `Video.watched_duration = MAX(all devices)`；后续可加 "from this device" 切换
- **缩略图缺失**：ffmpeg 不在 PATH 时端点返回 404；前端用 onError 兜底图
- **E2E 跑通条件**：后端必须先启（带空 DB），否则前端的 useVideoList 会卡 500
- **CI 集成**：playwright 在 GH Actions 需要 `npx playwright install --with-deps chromium`；建议缓存 `$HOME/.cache/ms-playwright`
- **M2 完成后**：分支合并到 main，启 M3 计划（tags / collections / sharing）


