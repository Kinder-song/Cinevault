# CineVault v2.0 Greenfield 重写设计文档

**日期**: 2026-06-01
**项目**: CineVault 视频库管理系统
**版本**: 2.0（Greenfield 重写）
**状态**: 设计阶段，待批准
**存放位置**: `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/`（v1 在 `../video_view/` 保留参考与数据迁移源）

---

## 1. 背景与目标

### 1.1 项目概述

CineVault 是一款自托管的本地视频管理 / 流媒体 Web 应用，2026 年 5 月已迭代到 1.x 形态（Flask + MySQL + 原生 JS + 玻璃拟态 UI）。本设计文档定义 v2.0 的完全重写：以**现代 Web 工程质量**和**极致用户体验**为目标，引入 FastAPI + React + TypeScript + HLS 转码 + PWA 等能力，同时保留并强化 v1 的核心功能。

### 1.2 目标

| 目标 | 度量 |
|---|---|
| 极佳用户体验 | 90+ Lighthouse Performance/Accessibility/Best Practices；首屏 < 1.5s；交互 < 100ms |
| 极佳美观度 | 统一设计 token；暗 / 亮双主题；A11y AA 合规；动效遵循 Material Motion 原则 |
| 高效执行 | 单实例支持 50+ 并发播放；HLS 自适应；缩略图 / 元数据缓存命中率 > 80% |
| 团队易理解 | 清晰分层架构；模块边界明确；任何 PR < 400 行 diff |
| 易修改 | 无循环依赖；命名一致；接口契约在 OpenAPI 一处定义 |
| 易测试 | 后端覆盖率 > 80%；前端组件测试 > 70%；E2E 覆盖核心路径 |
| 易演进 | 数据库用 Alembic 版本化；接口设计预留扩展点；新功能走 RFC 流程 |
| 安全稳健 | OWASP Top 10 全数通过；速率限制；CSRF；CORS；CSP；自动依赖审计 |

### 1.3 非目标（YAGNI）

- 不做云原生（不引入 K8s / 多副本）
- 不做企业级身份（OIDC、SSO）
- 不做商业 DRM（Widevine / FairPlay）
- 不做视频在线编辑、字幕在线编辑
- 不做实时协同（多人同时编辑标签）
- 不做 AI 自动打标 / 摘要 / 字幕生成（v2.1 候选）
- 不做 Chromecast / DLNA 投屏（v2.1 候选）
- 不做 Docker / 反向代理部署（按用户要求，纯本地 PWA）

---

## 2. 技术栈决策

### 2.1 后端

| 组件 | 选型 | 理由 |
|---|---|---|
| Web 框架 | **FastAPI 0.115+** | 异步原生、类型驱动、自动 OpenAPI、性能 2-3x Flask |
| ASGI 服务器 | **Uvicorn + Granian** | Granian 性能更稳定，Rust 加速 |
| 数据建模 | **SQLAlchemy 2.0 (async)** | 类型安全、AsyncSession、社区成熟 |
| 迁移 | **Alembic** | SQLAlchemy 官方迁移工具 |
| 校验 | **Pydantic 2** | FastAPI 内置、性能优秀 |
| 鉴权 | **PyJWT + passlib[bcrypt]** | 工业标准 |
| 任务队列 | **ARQ (asyncio Redis)** | 轻量、asyncio 原生；用进程内 fallback（`asyncio.Queue`）保证零依赖启动 |
| 缓存 | **进程内 LRU + 后续可换 Redis** | 单机部署够用 |
| 文件扫描 | **`scandir` + `watchfiles`** | 监听目录变更触发增量同步 |
| 转码 | **ffmpeg + ffprobe** | 复用 v1 的 `ffmpeg` 二进制 |
| 测试 | **pytest + pytest-asyncio + httpx** | 工业标准 |
| 静态检查 | **ruff + mypy --strict** | 单工具双角色 |
| 格式化 | **ruff format** | 与 lint 合一 |

### 2.2 前端

| 组件 | 选型 | 理由 |
|---|---|---|
| 框架 | **React 18 + TypeScript (strict)** | 生态最成熟 |
| 构建 | **Vite 5** | 启动 < 500ms；HMR 极快 |
| 路由 | **React Router 6 (data router)** | loader/action 模式 |
| 状态 | **Zustand + TanStack Query** | 轻量 + 服务端状态分离 |
| 样式 | **CSS Modules + Design Token (CSS Variables)** | 避免 Tailwind CDN 性能损耗；保留主题切换 |
| 动效 | **Framer Motion** | 声明式、性能好 |
| 视频 | **hls.js** | MSE HLS；Safari 原生支持 |
| 表格 / 列表 | **TanStack Table (headless)** | 高级过滤 / 排序的灵活性 |
| 表单 | **react-hook-form + zod** | 类型安全、性能好 |
| 测试 | **Vitest + Testing Library + Playwright** | 单测 + 组件测 + E2E |
| 类型 | **TypeScript 5.5+ (strict)** | strict + noUncheckedIndexedAccess |
| 工具 | **ESLint + Prettier** | 一体化 |

### 2.3 部署 / 工具链

| 用途 | 工具 |
|---|---|
| 进程管理 | `uv run` + `granian` 一条命令 |
| 静态资源 | 由 FastAPI 直接 serve（`/static`、`/manifest.webmanifest`） |
| PWA | Vite PWA plugin（Workbox） |
| CI | GitHub Actions（lint、type-check、test、build、bundle size） |
| 依赖审计 | `pip-audit` + `npm audit` |
| Pre-commit | `pre-commit` 框架 |
| 文档站点 | FastAPI 自动 Swagger UI + 内部 docs/ 目录 |

---

## 3. 架构

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│  Presentation (React + Vite SPA)                        │
│  - Pages / Components / Hooks / Stores                   │
│  - API client (openapi-typescript 自动生成)              │
└──────────────┬──────────────────────────────────────────┘
               │ HTTPS / JSON
┌──────────────▼──────────────────────────────────────────┐
│  Interface Layer (FastAPI Routers)                      │
│  - /api/v1/* REST endpoints                             │
│  - Request validation (Pydantic)                        │
│  - Auth dependencies                                    │
└──────────────┬──────────────────────────────────────────┘
┌──────────────▼──────────────────────────────────────────┐
│  Application Layer (Use Cases / Services)               │
│  - LibraryScanner, Transcoder, HlsSegmenter             │
│  - TagService, CollectionService, ShareService          │
│  - UserService, SyncService                             │
│  - 业务规则、跨实体编排                                  │
└──────────────┬──────────────────────────────────────────┘
┌──────────────▼──────────────────────────────────────────┐
│  Domain Layer (Pure Python, no I/O)                     │
│  - Entities (Video, Tag, Collection, User, Share)       │
│  - Value Objects (Resolution, Bitrate, Duration)         │
│  - Domain exceptions                                    │
└──────────────┬──────────────────────────────────────────┘
┌──────────────▼──────────────────────────────────────────┐
│  Infrastructure Layer (I/O)                              │
│  - SQLAlchemy async repos                               │
│  - FfmpegProbe / FfmpegTranscode                        │
│  - FileStorage (LocalFS abstraction)                    │
│  - HlsPackager                                          │
│  - PasswordHasher (bcrypt) / JwtService                 │
│  - InMemoryTaskQueue (ARQ fallback)                     │
└─────────────────────────────────────────────────────────┘
```

### 3.2 模块边界

**后端项目结构**：

```
cinevault/
├── pyproject.toml             # uv + ruff + mypy 配置
├── README.md
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── cinevault/
│       ├── __init__.py
│       ├── main.py            # FastAPI app factory
│       ├── config.py          # pydantic-settings
│       ├── core/              # 跨切面（无业务）
│       │   ├── auth.py        # JWT 签发与校验
│       │   ├── security.py    # 密码 hash、限流、防爆破
│       │   ├── logging.py     # 结构化日志（loguru）
│       │   ├── errors.py      # 统一异常 + handler
│       │   └── pagination.py
│       ├── domain/            # 纯领域（无 I/O）
│       │   ├── entities/
│       │   ├── value_objects/
│       │   └── exceptions.py
│       ├── application/       # 用例层
│       │   ├── library/       # 扫描 / 同步
│       │   ├── media/         # 元数据 / 转码 / 切片
│       │   ├── tags/
│       │   ├── collections/
│       │   ├── sharing/
│       │   ├── users/
│       │   └── playback/      # 观看进度
│       ├── infrastructure/    # I/O 适配
│       │   ├── db/
│       │   │   ├── models.py
│       │   │   ├── session.py
│       │   │   └── repos/
│       │   ├── storage/       # 文件系统抽象
│       │   ├── media/         # ffmpeg 包装
│       │   ├── tasks/         # 任务队列
│       │   └── security/      # JWT / bcrypt
│       ├── interface/         # 路由 / schema
│       │   ├── http/
│       │   │   ├── v1/
│       │   │   │   ├── videos.py
│       │   │   │   ├── tags.py
│       │   │   │   ├── collections.py
│       │   │   │   ├── share.py
│       │   │   │   ├── users.py
│       │   │   │   ├── auth.py
│       │   │   │   ├── dashboard.py
│       │   │   │   └── stream.py
│       │   │   └── deps.py    # FastAPI dependencies
│       │   └── schemas/       # Pydantic 输入输出
│       └── static/            # 前端构建产物（CDN 替代）
├── frontend/                  # 见下
├── data/                      # 视频 / 缩略图 / HLS 缓存 / SQLite 文件
│   ├── media/
│   ├── thumbnails/
│   ├── hls/
│   └── cinevault.db
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                   # Playwright
└── scripts/
    ├── init_db.py
    └── seed.py
```

**前端项目结构**：

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── public/
│   └── icons/
├── src/
│   ├── main.tsx
│   ├── app/
│   │   ├── router.tsx
│   │   ├── providers.tsx
│   │   └── layout/
│   ├── pages/
│   │   ├── library/
│   │   ├── player/
│   │   ├── dashboard/
│   │   ├── settings/
│   │   ├── auth/
│   │   └── share/
│   ├── features/              # 按业务功能垂直切分
│   │   ├── tags/
│   │   ├── collections/
│   │   ├── filters/
│   │   ├── sync/
│   │   └── player/
│   ├── components/            # 通用 UI 原子
│   │   ├── primitives/       # Button, Input, Dialog, Toast
│   │   ├── data/             # DataTable, FilterBar
│   │   ├── feedback/         # Skeleton, EmptyState, ErrorBoundary
│   │   └── media/            # Thumbnail, Poster, VideoCanvas
│   ├── api/                   # openapi-typescript 生成
│   │   ├── client.ts
│   │   ├── hooks.ts
│   │   └── schema.d.ts
│   ├── stores/                # zustand
│   ├── styles/
│   │   ├── tokens.css        # 设计 token（颜色、间距、圆角等）
│   │   ├── reset.css
│   │   ├── global.css
│   │   └── themes/           # dark/light
│   ├── hooks/                # 通用 hooks
│   ├── lib/                  # 工具（不含业务）
│   └── types/
├── tests/
│   ├── unit/
│   ├── component/
│   └── e2e/
└── playwright.config.ts
```

### 3.3 依赖方向

- Interface → Application → Domain ← Infrastructure
- 任何反向引用立即 lint 报错（用 ruff `TID252` 等规则）
- 前端不直连 DB，只走 API
- 任务队列：扫描 / 转码通过 `application/` 入队，`infrastructure/tasks/` 消费

### 3.4 错误处理

- 后端：自定义 `AppError` 体系 + FastAPI exception handler 统一响应格式 `{ code, message, details? }`
- 前端：TanStack Query 自动 retry / error boundary / toast
- 日志：loguru 结构化 JSON，按 request_id 关联

### 3.5 认证流程

1. 用户 POST `/api/v1/auth/login` → 后端校验 bcrypt → 签发 access_token (15min) + refresh_token (7d)
2. access_token 放 `Authorization: Bearer`；refresh_token 放 HttpOnly Secure SameSite=Strict cookie
3. 路由级 FastAPI dependency `current_user` 解析 token 注入
4. 自动刷新：前端拦截器遇到 401 调 `/api/v1/auth/refresh`
5. 防爆破：进程内 `LoginAttemptTracker`（v1 已有，迁移并增强）

---

## 4. 数据模型

### 4.1 ORM（SQLAlchemy 2.0 async）

```python
# 仅展示核心模型，详细字段在 Alembic 首个版本迁移中

class User:
    id: int (PK)
    username: str (UNIQUE, 50)
    email: str (UNIQUE, 100)         # 新增（v1 没有）
    password_hash: str (255)
    is_active: bool
    role: enum('owner', 'admin', 'user', 'guest')  # 多用户同步需要
    last_login_at: datetime?
    created_at: datetime
    updated_at: datetime


class Video:
    id: int (PK)
    user_id: int (FK users)          # 谁拥有/导入
    library_id: int (FK libraries)   # 属于哪个媒体库
    title: str (255)
    original_filename: str (500)
    storage_path: str (1000)         # 相对于 library root
    container: str (10)              # mp4 / mkv
    video_codec: str (50)?
    audio_codec: str (50)?
    width: int
    height: int
    duration_sec: decimal(10,2)
    bitrate_kbps: int
    framerate: decimal(5,2)
    file_size_bytes: bigint
    file_hash: str (64, sha256)      # 用于去重和变更检测
    mtime: int                       # 原始 mtime，便于增量
    thumbnail_path: str?             # 缩略图相对路径
    hls_master_path: str?            # HLS master.m3u8 相对路径
    transcode_status: enum('pending', 'processing', 'ready', 'failed')
    transcode_error: str?
    imported_at: datetime
    updated_at: datetime
    last_played_at: datetime?
    
    __table_args__ = (
        Index('ix_videos_library', 'library_id'),
        Index('ix_videos_hash', 'file_hash'),
        UniqueConstraint('library_id', 'storage_path', name='uq_video_path'),
    )


class Library:                        # 多媒体库支持
    id: int (PK)
    owner_id: int (FK users)
    name: str (100)
    root_path: str (1000)
    is_default: bool
    scan_status: enum('idle', 'scanning', 'error')
    last_scanned_at: datetime?
    created_at: datetime


class Tag:
    id: int (PK)
    name: str (50, UNIQUE)
    color: str (7)
    created_at: datetime


class VideoTag:
    video_id: int (FK, PK)
    tag_id: int (FK, PK)
    added_by: int (FK users)
    added_at: datetime


class Collection:
    id: int (PK)
    owner_id: int (FK users)
    name: str (100)
    description: text?
    is_public: bool                  # 分享给其他用户
    cover_video_id: int? (FK videos)
    created_at: datetime
    updated_at: datetime


class CollectionVideo:
    collection_id: int (FK, PK)
    video_id: int (FK, PK)
    position: int
    added_at: datetime


class PlaybackState:                  # 多设备同步
    id: int (PK)
    user_id: int (FK users)
    video_id: int (FK videos)
    device_id: str (100)             # UUID
    device_name: str? (100)
    position_sec: decimal(10,2)
    duration_sec: decimal(10,2)
    completed: bool
    last_heartbeat: datetime
    created_at: datetime
    updated_at: datetime
    
    __table_args__ = (
        UniqueConstraint('user_id', 'video_id', 'device_id', name='uq_state_device'),
        Index('ix_state_user_video', 'user_id', 'video_id'),
    )


class Device:                          # 已登录设备
    id: int (PK)
    user_id: int (FK users)
    device_id: str (100, UNIQUE)
    device_name: str?
    platform: str? (50)              # iOS / Android / macOS / Web
    last_active: datetime
    refresh_token_hash: str?         # 当前 refresh token 哈希
    created_at: datetime


class ShareToken:
    id: int (PK)
    token: str (64, UNIQUE)
    resource_type: enum('video', 'collection')
    resource_id: int
    created_by: int (FK users)
    expires_at: datetime
    revoked: bool
    password_hash: str?              # 可选密码保护
    max_views: int?                  # 限次
    view_count: int
    created_at: datetime


class UserPreferences:
    user_id: int (PK, FK users)
    theme: enum('dark', 'light', 'system')
    language: str (10)
    playback_speed: decimal(3,2)
    default_volume: int
    autoplay: bool
    updated_at: datetime
```

### 4.2 关键设计点

- **设备独立进度**：每个 (user, video, device) 独立 position，可选"汇总进度 = max(所有设备)"或"取最近心跳"。
- **多用户**：通过 `user_id` 隔离；库（Library）层面 owner 控制访问。
- **HLS 转码状态**：`transcode_status` 字段保证前端能查询；转码失败不阻塞主流程。
- **去重**：`file_hash`（sha256）支持识别同一文件被复制/移动。

### 4.3 索引策略

- `videos(library_id, storage_path)` 唯一索引
- `videos(file_hash)` 哈希索引（查重）
- `videos(transcode_status)` 过滤未转码
- `playback_states(user_id, video_id)` 跨设备同步
- `tags(name)` 唯一
- `share_tokens(token, expires_at)` 唯一 + 复合

---

## 5. API 设计

### 5.1 命名 / 规范

- RESTful、版本化（`/api/v1/`）
- 资源用复数名词
- 过滤用 query string，复杂查询用 `POST /search`
- 错误响应统一：
  ```json
  {
    "code": "video_not_found",
    "message": "Video not found",
    "details": { "video_id": 42 }
  }
  ```
- 分页用 cursor-based（`?cursor=...&limit=24`），避免大表 offset

### 5.2 核心端点

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/v1/auth/login` | 登录，返回 access + refresh |
| POST | `/api/v1/auth/refresh` | 刷新 access |
| POST | `/api/v1/auth/logout` | 登出（撤销 refresh） |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET | `/api/v1/videos` | 视频列表（搜索、过滤、分页、排序） |
| GET | `/api/v1/videos/{id}` | 视频详情 |
| POST | `/api/v1/videos/{id}/tags` | 加标签 |
| DELETE | `/api/v1/videos/{id}/tags/{tag_id}` | 删标签 |
| POST | `/api/v1/videos/{id}/playback` | 记录进度（device_id 自动注入） |
| GET | `/api/v1/videos/{id}/playback` | 查所有设备进度 |
| GET | `/api/v1/videos/{id}/stream.m3u8` | HLS master playlist |
| GET | `/api/v1/videos/{id}/stream/{quality}/index.m3u8` | 质量 variant |
| GET | `/api/v1/videos/{id}/stream/{quality}/segment-{n}.ts` | 切片 |
| GET | `/api/v1/videos/{id}/thumbnail.jpg` | 缩略图 |
| GET | `/api/v1/videos/{id}/subtitles/{filename}` | 字幕 |
| GET | `/api/v1/videos/{id}/screenshots/{filename}` | 关联图 |
| POST | `/api/v1/videos/{id}/share` | 创建分享 |
| GET | `/api/v1/videos/{id}/share` | 列出分享 |
| DELETE | `/api/v1/videos/{id}/share/{token_id}` | 撤销分享 |
| GET | `/api/v1/tags` | 标签列表（带计数） |
| POST | `/api/v1/tags` | 创建标签 |
| PATCH | `/api/v1/tags/{id}` | 改颜色 |
| DELETE | `/api/v1/tags/{id}` | 删标签（无视频引用时才允许） |
| GET | `/api/v1/collections` | 合集列表 |
| POST | `/api/v1/collections` | 新建合集 |
| PATCH | `/api/v1/collections/{id}` | 改元数据 |
| DELETE | `/api/v1/collections/{id}` | 删合集 |
| POST | `/api/v1/collections/{id}/videos` | 加视频（支持批量、位置） |
| PATCH | `/api/v1/collections/{id}/reorder` | 重排 |
| DELETE | `/api/v1/collections/{id}/videos/{video_id}` | 移除 |
| GET | `/api/v1/users/me` | 当前用户 |
| PATCH | `/api/v1/users/me` | 改用户名 / 头像 / 偏好 |
| POST | `/api/v1/users/me/password` | 改密码（需旧密码） |
| GET | `/api/v1/users/me/devices` | 设备列表 |
| DELETE | `/api/v1/users/me/devices/{id}` | 踢出设备 |
| GET | `/api/v1/libraries` | 库列表 |
| POST | `/api/v1/libraries` | 新建库 |
| POST | `/api/v1/libraries/{id}/scan` | 触发扫描 |
| GET | `/api/v1/libraries/{id}/scan/status` | 扫描状态（轮询或 SSE） |
| GET | `/api/v1/dashboard/stats` | 仪表盘统计 |
| GET | `/api/v1/dashboard/timeline` | 观看时间线（每日时长） |
| GET | `/api/v1/search/videos` | 高级搜索（多标签、时长区间、码率） |
| GET | `/share/{token}` | 公开分享页（SSR or SPA route） |
| GET | `/api/v1/share/{token}/resource` | 分享资源元数据（带密码校验） |
| GET | `/api/v1/share/{token}/stream.m3u8` | 分享 HLS |
| POST | `/api/v1/share/{token}/verify` | 验证分享密码 |

### 5.3 HLS 自适应

- 转码产 4 档：240p / 480p / 720p / 1080p（源分辨率低于目标档则跳过）
- 每档 6 秒切片，h.264 + AAC
- master.m3u8 列档位，BW-based ABR
- 同时保留"原画 fallback"：低带宽/老设备可走 MP4 渐进流

### 5.4 高级搜索示例

```http
POST /api/v1/search/videos
{
  "text": "travel",
  "tags": ["vlog", "4k"],
  "tag_logic": "AND",
  "duration_min": 60,
  "duration_max": 1800,
  "width_min": 1920,
  "codecs": ["h264", "hevc"],
  "favorite": true,
  "watched": "in_progress",
  "added_after": "2026-01-01",
  "sort": "last_played_desc",
  "cursor": null,
  "limit": 24
}
```

---

## 6. UI / UX 设计语言

### 6.1 设计原则

1. **内容优先**：视频缩略图是主角，UI 元素退后；播放器全屏时零干扰
2. **玻璃 + 动效**：保留 v1 玻璃拟态语言，但用 CSS Variables + GPU transform 优化
3. **可预测**：所有交互有 hover/active/disabled 三态，键盘可访问
4. **A11y First**：ARIA、focus ring、对比度 AA、reduced-motion 尊重

### 6.2 设计 Token（节选）

```css
:root {
  /* 颜色 - 暗 */
  --bg-base: #0A0814;
  --bg-elev-1: #14111E;
  --bg-elev-2: #1C1828;
  --bg-glass: rgb(20 17 30 / 0.65);
  
  --text-primary: #ECEAFF;
  --text-secondary: #A5A0D8;
  --text-muted: #6A6597;
  
  --accent-primary: #A78BFA;       /* 紫罗兰 */
  --accent-pink: #F0A5C0;
  --accent-cyan: #7DD3FC;
  --accent-success: #86EFAC;
  --accent-warning: #FCD34D;
  --accent-danger: #FCA5A5;
  
  /* 间距 / 圆角 / 阴影 */
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-6: 24px; --space-8: 32px; --space-12: 48px;
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --radius-xl: 24px;
  --shadow-md: 0 4px 12px rgb(0 0 0 / 0.4);
  --shadow-glass: 0 8px 32px rgb(0 0 0 / 0.35);
  
  /* 动效 */
  --motion-fast: 150ms;
  --motion-base: 220ms;
  --motion-slow: 360ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}

[data-theme="light"] {
  --bg-base: #FAF7FC;
  --bg-elev-1: #FFFFFF;
  --bg-elev-2: #F4EEF8;
  --bg-glass: rgb(255 255 255 / 0.75);
  --text-primary: #2D1B3D;
  /* ... */
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 6.3 关键页面

1. **Library（首页）**
   - 顶部：搜索条 + 过滤面板 + 视图切换（grid/list）+ 排序
   - 主体：Bento grid 视频卡片，hover 显示 5s 静默预览（来自原画或预生成 MP4 预览）
   - 空态：插画 + CTA

2. **Player**
   - 顶部导航（透明 → 滚动后不透明）
   - 中央：HLS 视频，键盘全快捷键
   - 右侧：元信息、字幕、截图、标签、收藏 / 评分、分享
   - 底部：播放列表

3. **Dashboard**
   - 顶部统计卡（总视频、总时长、已观看、收藏、剩余空间）
   - 中部：观看时间线、热门标签云、分辨率饼图
   - 底部：最近活动

4. **Settings**
   - Tabs：账户、播放、主题、库、设备、分享管理

5. **Share（公开）**
   - 不需要登录；若设了密码则先弹密码框
   - 极简播放器 + 视频信息

### 6.4 动效规范

- 卡片 hover：300ms ease-out 抬升 + 阴影
- 模态：240ms ease-out scale + opacity
- 路由切换：cross-fade 220ms
- 列表添加：spring (260ms) 滑入
- 列表删除：240ms 滑出 + 折叠

### 6.5 PWA

- Web App Manifest：name、icons（192/512）、display=standalone、theme_color
- Service Worker：Workbox 注入
  - 预缓存：app shell、字体
  - 运行时缓存：缩略图（CacheFirst + 30d）、HLS playlist + segments（StaleWhileRevalidate）
  - 离线回退页
- 安装提示：自定义 banner（不打扰）

---

## 7. 功能拆分与里程碑

### 7.1 里程碑总览

| M | 名称 | 周期 | 验收 |
|---|---|---|---|
| **M0** | 项目骨架 | 2-3 天 | 后端 Hello World + 前端 Hello World + CI 跑通 ruff/mypy/eslint/tsc |
| **M1** | 后端基座 | 4-5 天 | Auth (JWT/refresh) + Users + Alembic 初始 + 媒体库扫描 + ffprobe 元数据 + 直 MP4 流 |
| **M2** | 视频库 + 播放器 | 5-6 天 | 库页 + 卡片 + 过滤/排序 + 播放器 + 进度同步 + HLS 转码（v1 链路跑通） |
| **M3** | 标签 + 合集 + 分享 | 4-5 天 | 全部 CRUD + 分享密码/限次 + 公开分享页 |
| **M4** | 高级过滤 + 仪表盘 | 4-5 天 | 高级搜索 / 时间线 / 图表 |
| **M5** | 多设备同步 + 设置 | 3-4 天 | Device CRUD + 跨设备进度 + 设置页 |
| **M6** | PWA + 离线 + 性能调优 | 4-5 天 | Workbox 注入、缓存策略、Lighthouse 90+ |
| **M7** | UI demo 分支合并 + 设计打磨 | 5-6 天 | 视觉统一、动效统一、a11y 验证 |
| **M8** | 文档 + 上线 | 2-3 天 | README、用户手册、备份脚本、首次发布 |

合计约 35-45 工作日（单人节奏）。如果并行 UI demo 分支可压缩到 25-35。

### 7.2 M0 项目骨架（详细）

- 后端
  - `uv` 初始化项目
  - `pyproject.toml` 配 ruff、mypy、pytest
  - `src/cinevault/main.py`：FastAPI app factory + `/healthz`
  - `Dockerfile`（仅用于 CI，不必部署）
  - `.env.example`
- 前端
  - `npm create vite@latest`（React + TS）
  - 安装 React Router、Zustand、TanStack Query、Framer Motion
  - `tsconfig.json` strict + noUncheckedIndexedAccess
  - ESLint + Prettier
- CI
  - GitHub Actions: 后端（lint、type、test、build wheel）、前端（lint、type、test、build）
  - 缓存 pip / npm
- 验收
  - PR 触发后 5min 内出 lint+test+build 结果
  - 后端 `/healthz` 返回 200
  - 前端 dev server 起来，访问首页有 hello

### 7.3 M1 后端基座（详细）

- 用户 / 角色表迁移
- 密码 hash、access / refresh JWT
- `/auth/login` `/auth/refresh` `/auth/logout` `/auth/me`
- 限流中间件
- 媒体库 CRUD
- 扫描器：递归扫目录 → ffprobe 提取 → 写 Video（用 file_hash + mtime 增量）
- 流媒体：直接 MP4 渐进（不转码）作为 v0
- 测试：domain 单测 100%、auth 路由 90%+

### 7.4 M2 视频库 + 播放器（详细）

- 后端
  - `GET /videos` 带分页、过滤、排序
  - HLS 转码器：异步任务，输入 MP4 → 4 档 HLS
  - 切片器：写 m3u8 + ts 到 `data/hls/{video_id}/{quality}/`
  - master.m3u8 生成
  - 进度 API（按 device_id 记录）
- 前端
  - Library 页：grid 卡片 + 过滤栏 + 排序
  - Player 页：HLS 播放器 + 自定义控制条 + 进度条
  - 主题切换 + 减少动画支持
  - 数据 hooks（TanStack Query）

### 7.5 后续 M3-M8（按 M2 模式展开，由 writing-plans 技能产出具体任务）

> 本设计文档只列目标、范围、产出物和验收标准；具体执行步骤（按 M2 同等粒度）由 `writing-plans` 技能在 M0 之后逐个里程碑产出。

---

## 8. 测试策略

### 8.1 后端

- **单测**（pytest）：domain 层覆盖率 100%，application 层 80%+，infrastructure 层 60%+
- **集成**：httpx + ASGITransport 测 API 路由
- **E2E**（Playwright）：登录、上传、播放、分享
- **Fixtures**：sample.mp4（1MB 测试用）、sample.srt、sample.jpg

### 8.2 前端

- **单测**（Vitest）：hooks、stores、utils
- **组件**（Testing Library）：Button、Dialog、FilterBar、Card
- **E2E**（Playwright）：library → player → share 全流程

### 8.3 质量门

- CI 必过：lint、type、test、build、bundle size
- main 分支强制 squash merge
- 提交规范：Conventional Commits

---

## 9. 性能预算

| 指标 | 目标 |
|---|---|
| 首页 FCP | < 1.0s |
| 首页 LCP | < 1.5s |
| 首页 TTI | < 2.0s |
| Library 切页 | < 200ms（API）< 100ms（前端切换） |
| Player 首帧 | < 500ms（HLS） |
| 缩略图 LCP | < 800ms |
| JS bundle (gz) | < 200KB 主包 + 懒加载路由 |
| CSS (gz) | < 30KB |
| 后端 P95 | < 50ms（API），< 100ms（流媒体头） |

---

## 10. 安全

- 密码：bcrypt cost=12
- JWT：HS256 强 secret（≥32 字符），access 15min、refresh 7d
- Refresh token：HttpOnly + Secure + SameSite=Strict，rotation 模式
- 速率限制：login 5/min/ip，API 100/min/user
- CORS：仅允许本地 origin
- CSP：default-src 'self' + 必要例外
- HSTS（仅 HTTPS 部署时）
- 文件路径：所有用户输入路径都过 `Path.resolve().is_relative_to(base)` 校验
- 转码：白名单 codec、分辨率、码率上限
- 分享：token 用 `secrets.token_urlsafe(32)`；可选密码 + max_views + expires_at
- 依赖：CI 跑 `pip-audit` + `npm audit`，高危阻断合并

---

## 11. 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| HLS 转码吃 CPU，长视频慢 | M | 任务队列限并发；后台跑；前端显示"准备中"；提供原画 fallback |
| 桌面 / 移动浏览器 HLS 兼容性差异 | M | 用 hls.js（Chrome / Firefox / Edge），Safari 原生；老设备走 MP4 |
| v1 → v2 数据迁移 | M | 写迁移脚本：MySQL → SQLite；映射字段；保留原有视频；缩略图复制 |
| 单用户 PWA 安装后 Storage 限制 | L | IndexedDB 仅放元数据；视频在 SD；缩略图可清理 |
| 视频版权 | L | 仅本地自托管，不分发；分享链接限域限次 |
| 团队规模小 → 工具链成本 | M | 工具链一期投入，回报在 2 月后 |

---

## 12. 验收标准（M8 之后）

- [ ] 所有 M0-M7 验收项完成
- [ ] Lighthouse 移动 / 桌面 4 项 ≥ 90
- [ ] 后端测试覆盖率 ≥ 80%
- [ ] 前端测试覆盖率 ≥ 70%
- [ ] 没有 HIGH 级安全告警
- [ ] 用户手册 + 开发者文档完成
- [ ] 数据迁移脚本可回滚
- [ ] 已知 v1 缺陷全部修复（见附录）

---

## 附录 A：v1 缺陷清单（v2 必须修复）

1. `login_required` 重复定义
2. `except: pass` 静默吞错（>= 4 处）
3. DB schema 字段缺失（运行时容错而非迁移）
4. `init_database()` 在 import 时执行（不可测）
5. `LoginAttemptTracker` 内存状态，多 worker 不共享
6. `extract_metadata` 用 ffmpeg stderr 正则（脆弱）
7. `generate_thumbnail` 调 ffmpeg 两次（性能）
8. `index()` 每次请求做磁盘扫描
9. 共享 token 无 access log / 限次 / 密码
10. `settings.html` 用 Proxy 拦截 history.pushState（脆弱 hack）
11. `shared.html` 与 base 脱节，自成体系
12. `video.html` 683 行 + 400 行内联 JS
13. `style.css` 2794 行单文件
14. 前端 `window.xxx = xxx` 全局污染
15. 无 CSP / HSTS / 严格 CORS
16. 无 rate limit（除登录）
17. 无依赖审计
18. 无 CI

---

## 附录 B：与 v1 的差异

| 维度 | v1 | v2 |
|---|---|---|
| 框架 | Flask 3 | FastAPI 0.115+ |
| ORM | mysql-connector 原生 SQL | SQLAlchemy 2.0 async |
| 前端 | 原生 JS + Tailwind CDN | React 18 + TS + Vite + CSS Modules |
| 视频流 | MP4 渐进 + 2MB buffer | HLS 自适应 + 原画 fallback |
| 进度同步 | 单设备 | 多设备 |
| 认证 | Flask session + bcrypt | JWT + refresh rotation |
| 测试 | 1 个文件 | 后端 80%+、前端 70%+ |
| 工具链 | 裸 | ruff + mypy + eslint + prettier + vitest + pytest + Playwright + pre-commit + CI |
| 部署 | 纯本地 | 纯本地 PWA（强化） |
| 主题 | 玻璃拟态 CSS | 玻璃拟态 + token 系统 + A11y |

---

## 附录 C：开放问题

1. SQLite 还是回到 MySQL？（倾向 SQLite，单机零运维）
2. 是否需要"上传"功能（v1 没有，v2 需评估）？
3. 父级 / 角色权限粒度做到什么程度？
4. 仪表盘图表库：Recharts vs visx vs 自绘 SVG？（倾向 Recharts）
5. 后台任务是否需要 SSE 推送扫描进度？（倾向 SSE）

以上问题在 M0/M1 阶段确认。
