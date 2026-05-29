# CineVault 全面重构设计方案

**日期**: 2026-05-29
**项目**: CineVault 视频库管理系统
**版本**: 1.0

---

## 1. 背景与目标

### 1.1 项目概述

CineVault 是一个基于 Flask + MySQL 的个人视频库管理系统，提供视频浏览、播放、元数据管理、标签分类、收藏评分、分享链接等功能。前端使用玻璃态（glassmorphism）设计风格，支持明暗主题切换。

### 1.2 当前问题

| 类别 | 问题 | 严重程度 |
|------|------|----------|
| 安全 | 路径穿越漏洞（video_path 可被用户控制） | Critical |
| 安全 | 无 CSRF 保护 | High |
| 安全 | 无登录防爆破机制 | High |
| 安全 | 硬编码 SECRET_KEY | Medium |
| 架构 | app.py 1056 行单体文件 | High |
| 架构 | main.js 567 行聚合所有前端逻辑 | Medium |
| 架构 | 无 service layer，路由直接操作数据库 | Medium |
| 性能 | Dashboard 6 个独立 SQL 查询 | Medium |
| 性能 | 视频列表全量加载前端过滤 | Medium |
| 代码 | video.html 重复的 toast-container 和 resume-bar | Low |
| 代码 | serve_screenshot 永不到达的 return 语句 | Low |
| 代码 | 多处 bare except 隐藏错误 | Medium |

### 1.3 重构目标

1. **安全加固** - 修复所有安全漏洞
2. **架构重构** - 拆分单体应用为分层架构
3. **代码模块化** - 前端 JS 模块化拆分
4. **性能优化** - 数据库查询优化、缓存策略
5. **可维护性** - 统一错误处理、结构化日志
6. **可测试性** - 单元测试覆盖

---

## 2. 项目结构

```
video_view/
├── app.py                      # 主入口，仅做路由注册
├── config.py                   # 配置（已存在）
├── requirements.txt            # 依赖
│
├── routes/                     # 路由层
│   ├── __init__.py
│   ├── auth.py                 # 登录/登出
│   ├── videos.py               # 视频列表/播放/流
│   ├── tags.py                 # 标签管理
│   ├── collections.py          # 合集管理
│   ├── share.py                # 分享链接
│   ├── dashboard.py            # 仪表盘
│   └── user.py                 # 用户设置
│
├── services/                   # 业务逻辑层
│   ├── __init__.py
│   ├── video_service.py        # 视频元数据提取/缩略图
│   ├── db_service.py           # 数据库连接池/事务
│   └── sync_service.py         # 视频库同步
│
├── models/                     # 数据模型层
│   ├── __init__.py
│   └── database.py             # ORM模型/迁移
│
├── utils/                      # 工具函数
│   ├── __init__.py
│   ├── formatters.py           # 格式化工具
│   ├── security.py             # 安全工具
│   └── logger.py               # 日志工具
│
├── static/
│   ├── js/
│   │   ├── main.js             # 入口文件
│   │   └── modules/
│   │       ├── card.js          # 视频卡片组件
│   │       ├── player.js        # 播放器组件
│   │       ├── tags.js          # 标签管理
│   │       ├── theme.js         # 主题切换
│   │       ├── playlist.js      # 播放列表
│   │       ├── filter.js        # 搜索过滤
│   │       ├── toast.js         # 通知系统
│   │       └── utils.js         # 通用工具
│   └── css/
│       └── style.css           # 保持单文件，按组件分区
│
├── templates/
│   ├── base.html               # 基础模板
│   ├── index.html
│   ├── video.html              # 修复重复元素
│   ├── login.html
│   ├── dashboard.html
│   ├── settings.html
│   └── shared.html
│
└── docs/superpowers/specs/     # 设计文档
```

---

## 3. 安全加固

### 3.1 路径穿越防护

**问题位置**: update_user_profile 中的 video_path 设置

```python
# utils/security.py
def validate_video_path(base_path: str, user_provided_path: str) -> str | None:
    """
    验证用户提供的路径不会穿越 base_path。
    返回验证后的绝对路径，或 None 表示无效。
    """
    base = os.path.realpath(base_path)
    if not os.path.isabs(user_provided_path):
        joined = os.path.join(base, user_provided_path)
    else:
        joined = user_provided_path
    real = os.path.realpath(joined)
    if not real.startswith(base + os.sep) and real != base:
        return None
    return real
```

### 3.2 登录防爆破

```python
# utils/security.py
class LoginAttemptTracker:
    """基于内存的登录尝试追踪"""

    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 300):
        self._attempts: dict[str, list[float]] = {}
        self._lockouts: dict[str, float] = {}
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds

    def is_locked_out(self, ip: str) -> bool:
        if ip in self._lockouts:
            if time.time() < self._lockouts[ip]:
                return True
            del self._lockouts[ip]
        return False

    def record_failure(self, ip: str) -> int:
        now = time.time()
        if ip not in self._attempts:
            self._attempts[ip] = []
        self._attempts[ip] = [t for t in self._attempts[ip] if now - t < 600]
        self._attempts[ip].append(now)
        remaining = self.max_attempts - len(self._attempts[ip])
        if remaining <= 0:
            self._lockouts[ip] = now + self.lockout_seconds
            remaining = 0
        return remaining

    def record_success(self, ip: str):
        if ip in self._attempts:
            del self._attempts[ip]
        if ip in self._lockouts:
            del self._lockouts[ip]
```

### 3.3 其他安全措施

| 安全措施 | 实现位置 | 说明 |
|---------|---------|------|
| CSRF 保护 | utils/security.py | Flask-WTF 或自定义 token |
| Rate Limiting | utils/security.py | 基于 IP 的请求频率限制 |
| 输入验证 | 各路由 | 严格参数校验 |
| Session 安全 | app.py | HttpOnly, Secure, SameSite |
| SECRET_KEY 检查 | config.py | 生产环境必须使用强密钥 |
| CORS 限制 | app.py | 限制跨域请求源 |

---

## 4. 架构重构

### 4.1 app.py 简化

```python
# app.py - 简化后
from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展
    from services.db_service import init_db_pool, init_database
    init_db_pool()
    init_database()

    # 注册蓝图
    from routes.auth import auth_bp
    from routes.videos import videos_bp
    from routes.tags import tags_bp
    from routes.collections import collections_bp
    from routes.share import share_bp
    from routes.dashboard import dashboard_bp
    from routes.user import user_bp

    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(videos_bp, url_prefix='/')
    app.register_blueprint(tags_bp, url_prefix='/api')
    app.register_blueprint(collections_bp, url_prefix='/api')
    app.register_blueprint(share_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(user_bp, url_prefix='/api')

    return app

if __name__ == '__main__':
    from waitress import serve
    app = create_app()
    serve(app, host='0.0.0.0', port=55300, threads=8)
```

### 4.2 前端模块化

```
static/js/
├── main.js              # 入口，初始化各模块
└── modules/
    ├── card.js          # 视频卡片 hover/click 逻辑
    ├── player.js        # 播放器控制
    ├── tags.js          # 标签 CRUD
    ├── theme.js         # 主题切换
    ├── playlist.js      # 播放列表管理
    ├── filter.js        # 搜索过滤
    ├── toast.js         # 通知系统
    └── utils.js         # 通用工具函数
```

---

## 5. 性能优化

### 5.1 Dashboard 查询合并

```python
# services/db_service.py
def get_dashboard_stats() -> dict:
    """单次查询获取所有 Dashboard 统计"""
    with with_db_cursor() as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total_videos,
                COALESCE(SUM(duration), 0) as total_duration,
                COALESCE(SUM(file_size), 0) as total_size,
                COALESCE(SUM(progress > 0), 0) as watched_count,
                COALESCE(SUM(CASE WHEN is_favorite = 1 THEN 1 ELSE 0 END), 0) as favorites,
                COALESCE(SUM(CASE WHEN width >= 3840 THEN 1 ELSE 0 END), 0) as uhd,
                COALESCE(SUM(CASE WHEN width >= 1920 AND width < 3840 THEN 1 ELSE 0 END), 0) as fhd,
                COALESCE(SUM(CASE WHEN width >= 1280 AND width < 1920 THEN 1 ELSE 0 END), 0) as hd,
                COALESCE(SUM(CASE WHEN width > 0 AND width < 1280 THEN 1 ELSE 0 END), 0) as sd,
                COALESCE(SUM(duration * (progress > 0)), 0) as watched_duration
            FROM videos
        """)
        main_stats = cursor.fetchone()

        cursor.execute("""
            SELECT t.name, t.color, COUNT(vt.video_id) as cnt
            FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            GROUP BY t.id
            ORDER BY cnt DESC
            LIMIT 20
        """)
        tag_stats = cursor.fetchall()

        cursor.execute("""
            SELECT codec, COUNT(*) as cnt
            FROM videos
            WHERE codec != ''
            GROUP BY codec
        """)
        codec_stats = cursor.fetchall()
```

### 5.2 服务端过滤分页

```python
# routes/videos.py - API 支持过滤参数
@videos_bp.route('/api/videos')
@login_required
def api_videos():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    search = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'name')

    # 构建 WHERE 条件进行数据库级过滤
    # 而非全量加载后前端过滤
```

### 5.3 缓存策略

```python
# services/cache_service.py
class SimpleCache:
    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = ttl_seconds

    def get(self, key: str):
        if key in self._cache:
            value, expires_at = self._cache[key]
            if time.time() < expires_at:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value, ttl: int = None):
        expires_at = time.time() + (ttl or self._ttl)
        self._cache[key] = (value, expires_at)

video_meta_cache = SimpleCache(ttl_seconds=600)
thumbnail_cache = SimpleCache(ttl_seconds=3600)
```

---

## 6. 错误处理与日志

### 6.1 全局错误处理

```python
# app.py
@app.errorhandler(404)
def not_found(e):
    if request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    if request.accept_mimetypes.accept_json:
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500
```

### 6.2 结构化日志

```python
# utils/logger.py
import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    return logger
```

---

## 7. Bug 修复

### 7.1 video.html 重复元素

删除第 245-259 行的重复 toast-container 和 resume-bar，只保留 block content 开头的一份。

### 7.2 serve_screenshot 永不到达的 return

删除 `app.py:639` 的无效 return 语句。

---

## 8. 测试策略

### 8.1 单元测试

```python
# tests/test_security.py
def test_validate_video_path_prevents_traversal():
    result = validate_video_path('/safe/base', '../../../etc/passwd')
    assert result is None

def test_login_tracker_lockout():
    tracker = LoginAttemptTracker(max_attempts=3, lockout_seconds=60)
    for i in range(3):
        remaining = tracker.record_failure('127.0.0.1')
    assert tracker.is_locked_out('127.0.0.1')
    tracker.record_success('127.0.0.1')
    assert not tracker.is_locked_out('127.0.0.1')
```

### 8.2 API 集成测试

```python
# tests/test_videos_api.py
def test_video_list_requires_auth(client):
    response = client.get('/api/videos')
    assert response.status_code == 401
```

---

## 9. 实施顺序

1. **安全修复** - 路径穿越、防爆破、CSRF
2. **架构拆分** - app.py 路由拆分、services 层
3. **前端模块化** - main.js 拆分
4. **性能优化** - Dashboard 查询合并、服务端过滤
5. **Bug 修复** - 重复元素、无效代码
6. **错误处理与日志** - 全局错误处理器、日志系统
7. **测试覆盖** - 单元测试、集成测试

---

## 10. 风险评估

| 阶段 | 风险 | 缓解措施 |
|------|------|----------|
| 架构拆分 | 路由注册顺序问题 | 按依赖顺序逐步拆分 |
| 前端模块化 | 模块间通信破坏 | 保持 API 兼容 |
| 性能优化 | 缓存一致性问题 | 合理的缓存失效策略 |
| 安全修复 | 登录逻辑回归 | 充分测试登录流程 |