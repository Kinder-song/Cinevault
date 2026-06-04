# CineVault

> 私人本地视频档案库 + 流媒体 Web 应用。扫描本地视频文件，自动抽取元数据并生成缩略图，提供玻璃拟态 UI 的视频库与全功能播放器。

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![MySQL](https://img.shields.io/badge/MySQL-8.0-orange) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## ✨ 功能特性

### 🎞️ 视频库
- 玻璃拟态 **Bento Grid** 卡片，hover 600ms 后自动播放静音预览
- 网格 / 列表视图切换（`localStorage` 记忆）
- 多字段搜索：标题、标签、分辨率、帧率、码率
- 服务端分页（12/24/48/96/页）+ 排序 + 合集过滤
- 卡片上显示缩略图、播放进度、收藏 ❤️、评分 ★

### ▶️ 播放器
- HTML5 `<video>` + 完全自定义控件
- 键盘快捷键（YouTube 风格）：
  - `Space` / `K` — 播放/暂停
  - `J` / `L` — 后退/前进 10 秒
  - `←` / `→` — ±5 秒
  - `↑` / `↓` — 音量 ±10%
  - `F` — 全屏、`T` — 剧院模式、`P` — 画中画、`M` — 静音
  - `0`-`9` — 跳到 0%–90%
- 进度记忆：每 5 秒自动保存，回到视频时"继续播放"
- 侧边播放列表：点击切换不刷页
- 自动字幕（`.srt` / `.vtt` / `.ass`）+ 截图画廊

### 📊 仪表盘
- 统计卡：视频总数、总时长、总大小、收藏数、观看进度
- 图表：标签分布、编码格式分布、分辨率分布

### 🗂️ 组织 & 分享
- 标签（多对多，6 色）
- 合集（多对多）
- 时限分享链接（1h / 24h / 3d / 7d），免登录可访问

## 📸 截图

> 启动后访问 `http://localhost:55300/login`，账号 `admin` / `admin123`（首次登录强制改密）。

## 🚀 快速开始

### 准备
- Python 3.10+
- MySQL 8.0+
- ffmpeg（**项目自带 80MB 二进制**，无需另装）

### 安装运行

```bash
# 1. 装依赖
pip install -r requirements.txt

# 2. 写 .env（参考下面"配置"）
cp .env.example .env
vim .env

# 3. 把视频放进 video/ 目录（支持 .mp4 / .mkv / .webm / .mov / .avi / .m4v）

# 4. 启动
python3 app.py
```

访问 **http://localhost:55300**

首次登录：`admin` / `admin123`，系统会强制跳转去改密码。

## ⚙️ 配置

`.env` 文件：

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | Flask session 加密 key（用 `python3 -c "import secrets; print(secrets.token_hex(32))"` 生成） |
| `DB_HOST` | | `localhost` | MySQL 地址 |
| `DB_PORT` | | `3306` | MySQL 端口 |
| `DB_USER` / `DB_PASSWORD` | | `root` / 空 | MySQL 凭据 |
| `DB_NAME` | | `video` | 数据库名 |
| `VIDEO_PATH` | | `./video` | 视频目录 |
| `FFMPEG_PATH` | | `./ffmpeg` | ffmpeg 路径（用项目自带的就不要改） |

## 🛠 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python · Flask 3.0 · Waitress（生产 WSGI） |
| 数据库 | MySQL 8.0 · 连接池 |
| 视频处理 | ffmpeg（自带二进制） |
| 前端 | Jinja2 模板 + 原生 ES Module JavaScript（**无构建工具**） |
| 样式 | 手写 CSS（玻璃拟态）+ Tailwind（CDN 工具类） |
| 图标 | Lucide（CDN） |
| 认证 | bcrypt + Flask 文件 Session + 登录限流 |

## 🔌 API

应用以 JSON API 形式暴露数据，主要端点：

| 类别 | 端点 | 说明 |
|---|---|---|
| 认证 | `POST /login` · `GET /logout` | 登录登出 |
| 视频 | `GET /api/videos` | 列表（分页/搜索/排序） |
| 视频 | `GET /api/video/<f>/data` | 单视频完整数据 |
| 视频 | `POST /api/video/<f>/progress` | 保存播放进度 |
| 视频 | `POST /api/video/<f>/favorite` | 切换收藏 |
| 视频 | `POST /api/video/<f>/rating` | 设置评分 0-5 |
| 视频 | `POST /api/video/<f>/tags` · `DELETE /api/video/<f>/tags/<t>` | 标签管理（**admin only**） |
| 视频 | `POST /api/video/<f>/share` | 生成分享 token |
| 视频 | `POST /api/video/<f>/refresh-thumb` | 重新生成缩略图（**admin only**） |
| 视频 | `GET /stream/<f>` · `GET /thumbnail/<f>` · `GET /subtitle/<f>` | 流 / 缩略图 / 字幕 |
| 合集 | `GET/POST /api/collections` · `DELETE /api/collections/<id>` | 列表/创建/删除（删除 **admin only**） |
| 合集 | `GET /api/collections/<id>` | 详情 |
| 合集 | `POST/DELETE /api/collections/<id>/videos[ /<f>]` | 加减视频（**admin only**） |
| 用户 | `GET/POST /api/user/profile` | 取 / 改资料 |
| 共享 | `GET /share/<token>` | 免登录访问分享 |
| 仪表盘 | `GET /dashboard` | 统计 + 图表 |
| 公共 | `GET /health` | 健康检查 |

> **管理端点**（收藏/评分/分享/合集/标签的写操作）需要 `admin` 用户身份。

## 📂 项目结构

```
CineVault/
├── app.py              # Flask 入口
├── config.py           # 环境配置
├── ffmpeg              # 80MB 自带二进制
├── fix_thumbnails.py   # 维护者工具：缩略图自愈
├── routes/             # 7 个 Blueprint（auth / videos / tags / collections / share / dashboard / user）
├── services/           # 数据/业务层（DB / 视频元数据 / 增量同步）
├── utils/              # 安全 / 格式化 / 日志
├── templates/          # 9 个 Jinja 模板
├── static/             # CSS + 5 个 JS module
├── tests/              # pytest
├── video/              # 你的视频放这里
├── thumbnails/         # 自动生成的 jpg
└── sessions/           # Flask session 文件
```

## 🧪 测试

```bash
pip install pytest
pytest tests/
```

测试覆盖：路径穿越防护、登录限流。

## 🐛 常见问题

**Q: 缩略图一直 404？**
A: 浏览器 `Ctrl+Shift+R` 硬刷；或在 Settings 里点"刷新封面"。

**Q: ffmpeg 报"not found"？**
A: 项目自带 `./ffmpeg` 二进制。如果你删了或改了路径，在 `.env` 设 `FFMPEG_PATH`。

**Q: MySQL 连接失败？**
A: 确认 `.env` 里 `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` 正确；确认 MySQL 监听 `0.0.0.0` 或具体 IP（不是 `localhost`）。

**Q: 端口 55300 已被占用？**
A: 改 `app.py` 末尾 `serve(...)` 的 `port=` 参数。

**Q: 如何修改默认账号？**
A: 启动后登录 → Settings → 改用户名 / 密码 / 视频目录。

## 🤝 贡献

欢迎 PR。所有功能改动请在 PR 描述里说明：
- 改动的目的
- 是否引入了新的环境变量
- 是否影响 schema（如有，写迁移步骤）

## 📄 License

MIT
