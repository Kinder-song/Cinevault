# CineVault

> 私人本地视频档案库 + 流媒体 Web 应用。扫盘、抽元数据、生成缩略图，给你一个带玻璃拟态 UI 的私人网飞。

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![MySQL](https://img.shields.io/badge/MySQL-8.0-orange) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## ✨ 主要功能

### 🎞️ 视频库
- **Bento Grid** 玻璃拟态卡片，hover 时 600ms 触发静音预览（同时最多 3 个）
- **网格 / 列表** 视图切换，状态写入 `localStorage`
- **多字段搜索**：标题、标签、分辨率、帧率、码率（100ms debounce）
- **服务端分页**：12 / 24 / 48 / 96 / 页
- **合集过滤**、**按名称/大小/日期排序**
- 卡片上展示**缩略图**、**进度条**、**收藏** ❤️、**评分** ★

### ▶️ 播放器
- HTML5 `<video>` + **完全自定义控件**
- **键盘快捷键**（YouTube 风格）：
  - `Space` / `K` — 播放/暂停
  - `J` / `L` — 后退/前进 10 秒
  - `←` / `→` — ±5 秒
  - `↑` / `↓` — 音量 ±10%
  - `F` — 全屏、`T` — 剧院模式、`P` — 画中画、`M` — 静音
  - `0`-`9` — 跳到 0%-90%
- **进度记忆**：每 5 秒自动 POST，回到视频时弹"继续播放"
- **侧边播放列表**：点击切换视频不刷页
- **自动字幕**（`.srt` / `.vtt` / `.ass`）+ **截图画廊**（lightbox）

### 📊 仪表盘
- 5 个统计卡（视频数 / 总时长 / 总大小 / 收藏 / 观看进度）
- 3 个图表：标签分布、编码格式分布、分辨率分布（4K / 1080p / 720p / SD）

### 🗂️ 组织与协作
- **标签**（多对多，6 色随机）
- **合集**（多对多）
- **收藏** / **1-5 星评分** / **播放进度**
- **分享链接**：1h / 24h / 3d / 7d 时限 token，免登录可访问

### 🔐 安全
- **bcrypt** 密码哈希
- **登录限流**：5 次失败 → 锁 300 秒
- **路径穿越防护**（`validate_video_path`，附 6 个 pytest）
- **首次登录强制改密码**

## 🛠️ 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.10+ · Flask 3.0 · Waitress 3.0（生产 WSGI，8 线程） |
| 数据库 | MySQL 8.0 · mysql-connector-python · 8 连接池 |
| 视频处理 | ffmpeg（自带 80MB 二进制，无系统依赖） |
| 前端 | Jinja2 模板 + 原生 ES Module JS（**无构建工具**） |
| 样式 | 手写 CSS（2700+ 行，玻璃拟态）+ Tailwind（CDN 工具类） |
| 图标 | Lucide（CDN 懒加载） |
| 认证 | bcrypt + Flask 文件 Session + 登录限流 |
| 字体 | Outfit / Nunito / JetBrains Mono（Google Fonts） |

## 📂 项目结构

```
video_view/
├── app.py                      # 入口（Waitress 启动）
├── config.py                   # 环境配置
├── ffmpeg                      # 80MB 自带二进制
├── fix_thumbnails.py           # 一次性缩略图自愈脚本
├── requirements.txt
├── .env                        # DB 地址 / SECRET_KEY
│
├── routes/                     # 7 个 Flask Blueprint
│   ├── auth.py                 #   /login /logout + login_required
│   ├── videos.py               #   主页 / 详情 / 流 / 缩略图 / 字幕 / 截图 + 8 个 API
│   ├── tags.py                 #   视频标签
│   ├── collections.py          #   视频合集
│   ├── share.py                #   时限分享链接
│   ├── dashboard.py            #   /dashboard
│   └── user.py                 #   /settings + 用户资料
│
├── services/                   # 数据/业务层
│   ├── db_service.py           #   连接池 + 建表 + 仪表盘 SQL
│   ├── video_service.py        #   ffmpeg 元数据 + 缩略图 + 字幕/截图扫描
│   └── sync_service.py         #   增量同步（size + mtime 短路）
│
├── utils/
│   ├── security.py             #   路径校验 + 登录限流
│   ├── formatters.py           #   时长/码率/帧率/体积格式化
│   └── logger.py               #   4 个命名 logger
│
├── templates/                  # 9 个 Jinja 模板
│   ├── base.html               #   顶部导航 + 主题 + main.js
│   ├── index.html              #   视频库（卡片 + 分页 + 过滤）
│   ├── video.html              #   播放器页（控件 + 剧院 + PiP + 分享）
│   ├── dashboard.html          #   统计 + 图表
│   ├── login.html              #   登录
│   ├── settings.html           #   账户设置
│   ├── shared.html             #   免登录分享页
│   ├── 404.html / 500.html
│
├── static/
│   ├── css/style.css           # 2731 行手写玻璃拟态
│   └── js/
│       ├── main.js             #   入口（动态 import player）
│       └── modules/            # 5 个原生 ES Module
│           ├── theme.js        #     暗 / 亮主题
│           ├── toast.js        #     滑入通知 + 图标刷新
│           ├── card.js         #     卡片 hover 预览
│           ├── tags.js         #     卡片上的标签
│           └── player.js       #     播放器全部逻辑
│
├── tests/test_security.py      # 10 个 pytest
│
├── video/                      # 视频源目录（17 个 .mp4 / .mov）
├── thumbnails/                 # 自动生成的 jpg 缩略图
└── sessions/                   # Flask 文件 session
```

## 🚀 快速开始

### 1. 准备环境
- Python 3.10+
- MySQL 8.0+（远程或本地）
- ffmpeg（**项目自带 80MB 二进制，无需另装**）

### 2. 装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置 `.env`
```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=video
SECRET_KEY=请改成强随机字符串
VIDEO_PATH=./video
FFMPEG_PATH=./ffmpeg
```

### 4. 放视频
把 `.mp4` / `.mkv` / `.webm` / `.mov` / `.avi` / `.m4v` 放进 `video/` 目录。

### 5. 启动
```bash
python3 app.py
```
访问 **http://localhost:55300**

### 6. 首次登录
- 用户名：`admin`
- 密码：`admin123`
- **首次登录会强制跳转去改密码**

## 🔌 API 速查

### 视频
| 方法 | 端点 | 说明 |
|---|---|---|
| GET | `/` | 视频库主页 |
| GET | `/video/<f>` | 播放器页 |
| GET | `/stream/<f>` | 视频流（支持 HTTP Range） |
| GET | `/thumbnail/<f>` | 缩略图（自动懒生成） |
| GET | `/subtitle/<f>` / `/screenshot/<f>` | 字幕 / 截图 |
| GET | `/api/videos` | 列表 + 分页 + 搜索 + 排序 |
| GET | `/api/video/<f>/data` | 单视频完整数据包（切换时用） |
| POST | `/api/video/<f>/progress` | 保存播放进度 |
| POST | `/api/video/<f>/favorite` | 切换收藏 |
| POST | `/api/video/<f>/rating` | 设置评分 0-5 |
| POST | `/api/video/<f>/refresh-thumb` | 重新生成缩略图 |
| POST | `/api/video/<f>/share` | 生成分享 token |
| POST | `/api/video/<f>/tags` | 加标签 |
| DELETE | `/api/video/<f>/tags/<t>` | 删标签 |

### 合集 / 用户 / 仪表盘
| 方法 | 端点 | 说明 |
|---|---|---|
| GET / POST | `/api/collections` | 列出 / 创建 |
| DELETE | `/api/collections/<id>` | 删除 |
| GET | `/api/collections/<id>` | 详情 + 视频列表 |
| POST | `/api/collections/<id>/videos` | 加视频到合集 |
| DELETE | `/api/collections/<id>/videos/<f>` | 从合集移除 |
| GET | `/api/user/profile` | 取用户资料 |
| POST | `/api/user/profile` | 改用户名 / 密码 / 视频路径 |
| GET | `/dashboard` | 仪表盘页 |
| GET | `/share/<token>` | 免登录访问分享 |
| GET | `/health` | 健康检查 |

## 🗄️ 数据模型

```
users             用户
videos            视频（filename、duration、width/height、codec、bitrate、fps、
                  favorite、rating、watched_duration、thumbnail_path…）
tags              标签（name、color）
video_tags        视频-标签多对多
collections       合集
collection_videos 合集-视频多对多
share_tokens      分享 token（video_filename、expires_at）
```

`videos.favorite` / `watched_duration` / `share_tokens.video_filename` 是当前 schema 的实际列名。表结构在服务首次启动时由 `services/db_service.py:init_database()` 自动建好。

## ⚙️ 配置

| 变量 | 必填 | 说明 | 默认 |
|---|---|---|---|
| `SECRET_KEY` | ✅ | Flask session 加密 key | — |
| `DB_HOST` | | MySQL 地址 | `localhost` |
| `DB_PORT` | | MySQL 端口 | `3306` |
| `DB_USER` | | MySQL 用户 | `root` |
| `DB_PASSWORD` | | MySQL 密码 | （空）|
| `DB_NAME` | | 数据库名 | `video` |
| `VIDEO_PATH` | | 视频目录 | `./video` |
| `FFMPEG_PATH` | | ffmpeg 二进制路径 | `./ffmpeg` |
| `THUMBNAIL_DIR` | | 缩略图目录 | `thumbnails` |

## 🛠️ 工具脚本

### `fix_thumbnails.py` — 缩略图自愈
历史数据可能出现"DB 写了路径但磁盘没文件"或"文件在旧目录 `video/thumbnails/`"的不一致。运行：
```bash
python3 fix_thumbnails.py --regen-missing
```
- 优先把孤儿文件从遗留目录搬到正确位置
- 移动失败时用 ffmpeg 重新生成
- 加 `--cleanup-legacy` 删除空了的遗留目录

## ⚡ 性能要点

- **Waitress 8 线程** + **2MB socket 缓冲** + **2MB 文件 I/O 缓冲**
- **MySQL 连接池**（8 持久连接）
- **HTTP Range** 支持（视频流跳播）
- **增量同步**：`os.stat` 取 `size + mtime`，与 DB 比对，**只对变化的文件跑 ffmpeg**
- **RAF 批处理**：`timeupdate` 事件用 `requestAnimationFrame` 节流
- **缩略图并发控制**：hover 预览最多同时 3 个
- **搜索 debounce** 100ms

## 🧪 测试
```bash
pip install pytest
pytest tests/
```
覆盖：路径穿越防护、登录限流（10 个用例）。

## 🐛 常见问题

**Q: 缩略图一直 404？**
A: 检查 `THUMBNAIL_DIR` 与 `Config.THUMBNAIL_DIR` 一致；浏览器 Ctrl+Shift+R 硬刷；跑 `fix_thumbnails.py --regen-missing`。

**Q: ffmpeg 报"not found"？**
A: 默认走 `./ffmpeg`（项目自带二进制）。如要换路径，在 `.env` 改 `FFMPEG_PATH`。

**Q: 首次启动 MySQL 表结构对不上？**
A: 当前 schema 字段名是 `favorite` / `watched_duration` / `video_filename`。如果是从更老版本升上来，参考 `fix_thumbnails.py` 的自愈模式写迁移。

## 📝 更新日志

### 2026-06 重构要点
- 缩略图统一到 `Config.THUMBNAIL_DIR`（修过路由找 `thumbnails/`、代码写 `video/thumbnails/` 的目录 bug）
- `refresh-thumb` 端点改成"成功才返 200"，失败返 500 + 明确错误
- `routes/videos.py` 8 个死 import 清理 + 去重 `login_required`
- `static/js/modules/player.js` 9 个只内部用的 `export` 去掉
- `static/js/modules/filter.js` / `playlist.js` / `utils.js` 三个 stub 模块删除
- 清理 `cache/` `transcoded/` `__pycache__/` `.DS_Store` 等遗留

## 📄 License

MIT
