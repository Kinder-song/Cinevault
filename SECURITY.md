# 安全策略 / Security Policy

## 概述

CineVault 是面向**单用户或小团队**的本地部署视频档案库，威胁模型假设：

- 部署在受信网络（家庭 / 办公局域网），或经过一层反向代理对外暴露
- 不会暴露在公网无防护的根路径
- 攻击者模型：好奇邻居、外部未授权用户、被入侵的客户端浏览器

本文件记录已发现并修复的漏洞、当前安全模型、以及部署建议。

## 漏洞修复历史

以下漏洞在 **Plan 1: P0 安全加固** 期间（`959366a` → `1c73e00`）已全部修复：

| # | 严重度 | 漏洞描述 | 修复提交 |
|---|--------|----------|----------|
| 1 | 🔴 严重 | **任意文件读取** — 用户在个人资料中设置 `video_path` 可指向文件系统任意目录，结合 `/stream/` 即可读取系统文件 | [`959366a`](https://github.com/example/cinevault/commit/959366a) |
| 2 | 🔴 严重 | **路径穿越** — `/screenshot/` 端点未对 `filename` 做校验，`../../etc/passwd` 类 payload 可逃逸出 `screenshots/` 目录 | [`64be06e`](https://github.com/example/cinevault/commit/64be06e) |
| 3 | 🔴 严重 | **登录限流绕过** — 攻击者可伪造 `X-Forwarded-For` 头让应用将每个失败登录归到不同 IP，绕过 5 次/5 分钟的限流 | [`86d67d9`](https://github.com/example/cinevault/commit/86d67d9) |
| 4 | 🟠 高 | **共享页 stream URL 错误** — `shared.html` 模板变量名不匹配（`video.file` vs `video.filename`），导致分享链接 404 | [`662b6b2`](https://github.com/example/cinevault/commit/662b6b2) |
| 5 | 🟠 高 | **信息泄露** — 异常处理把原始 SQL / Python traceback 写进 500 响应，给攻击者提供 schema 与路径线索 | [`81a6fd6`](https://github.com/example/cinevault/commit/81a6fd6) |
| 6 | 🟠 高 | **CSRF 缺失** — 所有 POST / PUT / DELETE 端点未启用 CSRF 保护，恶意跨站页面可代用户提交 | [`7334e36`](https://github.com/example/cinevault/commit/7334e36) |
| 7 | 🟠 高 | **IDOR** — 合集 / 标签的写操作未校验 `admin` 身份，普通用户可改 / 删他人资源 | [`10cc307`](https://github.com/example/cinevault/commit/10cc307) |
| 8 | 🟡 中 | **输入校验缺失** — `progress` / `rating` / `favorite` 等接口未对 `int()` 输入做边界校验，可能写入非法值 | [`bf1f5c7`](https://github.com/example/cinevault/commit/bf1f5c7) |
| 9 | 🟡 中 | **分享 token 边界** — `hours` 参数未做范围限制，可创建永久 / 负时长分享 | [`1c73e00`](https://github.com/example/cinevault/commit/1c73e00) |

> 坦诚记录已修复的漏洞，是希望用户在自部署时了解威胁面，并按下方 **部署建议** 加固。

## 当前安全模型

### 1. 视频目录白名单（`VIDEO_ROOTS`）
- 用户在 Settings 中设置的 `video_path` **必须**落在 `VIDEO_ROOTS` 白名单内
- 默认白名单 = `os.path.abspath('./video')`
- 可通过 `VIDEO_ROOTS` 环境变量追加（逗号分隔绝对路径），用于外接硬盘等场景
- 服务端用 `os.path.realpath` 解析后比对白名单前缀，符号链接不绕过

### 2. CSRF 防护
- 使用 [`flask-seasurf 2.0`](https://flask-seasurf.readthedocs.io/) 保护所有 POST / PUT / DELETE 端点
- 客户端在 `static/js/main.js` 的 `fetch` 包装器中**自动**附加 `X-CSRF-Token` 请求头
- **仅登录接口（`/login`）豁免**：登录前还没有 session，无法携带 token
- 403 响应携带明确 `reason` 字段，便于客户端识别 CSRF 失败

### 3. 反向代理信任（`PROXY_FIX_DEPTH`）
- 使用 `werkzeug.middleware.proxy_fix.ProxyFix` 处理 `X-Forwarded-For`
- `PROXY_FIX_DEPTH` 显式指定可信代理层数（默认 `0`，无代理）
- 部署在反代后必须设为正确值（通常 `1`），否则客户端 IP 识别错误

### 4. SQL 注入防护
- **所有**查询通过 `repositories/` 层（`VideoRepository` / `UserRepository` / `CommentRepository` 等共 8 个）
- 全部使用 `mysql-connector-python` 的参数化语句
- 无字符串拼接 SQL

### 5. 路径穿越防护
- `/screenshot/` 等端点使用 `os.path.basename()` + `os.path.realpath()` 双重校验
- 文件名不合法或解析后不在预期目录内，直接 400 拒绝

### 6. 暴力破解防护
- `LoginAttemptTracker`（内存计数器）：同一 IP **5 次失败后锁定 5 分钟**
- `PROXY_FIX_DEPTH=0` 时 `X-Forwarded-For` 不被信任，从源头防止伪造

### 7. 密码安全
- `bcrypt 4.x` 加盐哈希（自动 salt）
- 默认账号 `admin` 首次登录**强制改密**（`admin123` 不能复用）
- 明文密码绝不写入日志

### 8. 错误响应净化
- 全局异常处理器（[`utils/errors.py`](./utils/errors.py)）只返回通用 `{"error": "Internal server error"}`
- 完整 traceback 与 SQL 错误写入**服务端** logger，**绝不**回给客户端
- 403（CSRF 失败）单独处理，返回 403 + 描述，便于合法客户端识别

### 9. 分享 token 边界
- `hours` 参数强制 clamp 到 `[1, 168]`
- 使用时区感知 `datetime`，避免多时区部署下 token 提前失效

## 部署建议

### 必做项

1. **`SECRET_KEY` 必填且唯一**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   写入 `.env`，**永远不要**提交到 git 或回显到日志

2. **`.env` 纳入 `.gitignore`**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **修改默认 admin 密码**
   首次启动后立即通过 Settings 改密

### 反向代理后部署

4. **`PROXY_FIX_DEPTH` 设为实际层数**
   - 直连：`0`（默认）
   - 一层反代（Caddy / Nginx）：`1`
   - 多层（CDN + 反代）：依次累加

5. **保留自定义请求头**
   - 应用依赖 `X-CSRF-Token` 头
   - **不要**在反代层做下划线 ↔ 连字符重写
   - Nginx 示例：`proxy_pass_request_headers on;`（默认开启）

6. **启用 HTTPS**
   - 强制 `Secure`、`HttpOnly` cookie
   - 推荐 Caddy（自动 ACME）或 Nginx + certbot

### 数据库

7. **MySQL 账号最小权限**
   - 只给 `video` 库
   - 监听 `127.0.0.1` 或内网 IP，不直接暴露 `0.0.0.0:3306`

8. **数据库密码强度**
   - 不少于 16 字符

### 文件系统

9. **运行账号只读视频目录**
   ```bash
   chown -R cinevault: cinevault /srv/cinevault/video
   chmod -R 750 /srv/cinevault/video
   ```
10. **缩略图 / 会话目录**给运行账号读写权限即可

### 保持更新

11. 关注以下组件的安全公告：
    - [Flask](https://github.com/pallets/flask/security)
    - [flask-seasurf](https://github.com/maxcountryman/flask-seasurf)
    - [mysql-connector-python](https://www.mysql.com/products/connector/)
    - [Werkzeug](https://github.com/pallets/werkzeug/security)

## 漏洞报告

如发现未修复的安全问题：

- **邮件**：`security@example.com`（请替换为实际地址）
- **GitHub**：开 Issue 并标记 `security`，**请勿**在公开 Issue 中披露 PoC 细节
- **响应时间**：48 小时内确认，严重问题 7 天内修复

我们承诺在修复前不追究善意研究者的责任。
