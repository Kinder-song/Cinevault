# 更新日志

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [Unreleased] — 2026-06-05

5 计划重构收尾，含以下模块化变更：

### 安全 (Plan 1: P0 加固)

`959366a` → `1c73e00`，共 8 个提交

- 用户 `video_path` 限制在 `VIDEO_ROOTS` 白名单内（`959366a`）
- 修复 `/screenshot/` 路径穿越漏洞（`64be06e`）
- 修复 `X-Forwarded-For` 伪造绕过登录限流（`86d67d9`）
- 修复共享页 `shared.html` 模板变量错误（`662b6b2`）
- 错误响应净化，阻止 SQL / 堆栈信息泄露（`81a6fd6`）
- 引入 `flask-seasurf 2.0`，所有写接口启用 CSRF（`7334e36`）
- `progress` / `rating` / `favorite` 强制 `int()` 校验（`bf1f5c7`）
- 分享 token 时长 clamp 到 `[1, 168]` 小时并改用时区感知 `datetime`（`1c73e00`）
- 合集 / 标签的写操作加 `admin_required` 装饰器，闭合 IDOR（`10cc307`）

### 性能 (Plan 2: 同步与缩略图)

`248f3dd` → `91550cf`，共 7 个提交

- 新增 `LibraryCache`（mtime 增量扫描）（`248f3dd`）
- 同步仅对 `(size, mtime)` 变化的视频做 ffmpeg 探测（`358dd16`）
- 元数据抽取与缩略图合并为单次 ffmpeg 调用（`a374a5c`）
- 缩略图生成移至后台线程 worker（`e3a81fc`）
- 新增可选的文件系统监听（`ENABLE_FS_WATCHER=1`）（`7fe54ec`）
- 修正 `/api/videos` 排序 / 过滤 / 分页执行顺序（`7e9541d`）
- 新增 1000 文件扫描基准测试（`91550cf`，`@pytest.mark.slow`）

### 架构 (Plan 3: Repository 层 + 模块化)

`401bae1` → `2ca21a1`，共 11 个提交

- 抽取 `VideoRepository`（`401bae1`）
- 抽取 `UserRepository`（`38a3342`）
- 抽取 `Tag` / `Collection` / `Share` / `Stats` repositories（`9c52c9c`）
- `tags` 路由切换到 `TagRepository` + `VideoRepository`（`889710a`）
- `collections` 路由切换到 `CollectionRepository`，清理重复 import（`0e2ddb1`）
- `user` 路由切换到 `UserRepository`（`9f69029`）
- `share` 路由切换到 `ShareRepository`（`ff549fa`）
- `dashboard` 路由切换到 `StatsRepository`；删除 `db_service.get_dashboard_stats` 包装（`5bef965`）
- 单体 `routes/videos.py`（562 行）拆分为 3 个 blueprint：`index` / `player` / `api_videos`（`6034db9`）
- `static/css/style.css`（2731 行）拆为 4 个模块：`tokens` / `glass` / `cards` / `player`（`5e85696`）
- 新增 Repository 集成测试，`INTEGRATION_DB=1` 时启用（`2ca21a1`）

### 核心功能 (Plan 4: 评论 & 观看历史)

`3a7f2fa` → `c9acd19`，共 7 个提交

- 新增 `comments` 与 `watch_history` 表（FK CASCADE，删视频自动清理）（`3a7f2fa`）
- 新增 `CommentRepository`（`1774e3d`）与 `HistoryRepository`（`57cb60a`）
- 新增 `/api/video/<f>/comments` 端点（`GET` / `POST` / `DELETE`）（`284b611`）
- 视频页新增评论 UI：XSS-safe 转义、最长 2000 字、作者本人或 admin 可删（`bb0ef97`）
- 观看进度保存时同步记录 `watch_history`；新增 `/history` 页面（最近 100 次观看）（`c8c5216`）
- 首页新增"最近观看"视频轨道（`c9acd19`）

### UX / 可访问性 (Plan 5: a11y 与体验打磨)

`29d26f0` → `5618032`，共 8 个提交

- 视频卡片由 `div` 改为 `<a>` 元素，键盘 Tab 可达（`29d26f0`）
- `<video>` 错误覆盖层 + 离线提示横幅（`0e7f39f`）
- 截图 lightbox 支持键盘（`Esc` 关闭、`role="dialog"`）（`844af90`）
- 进度条 `buffered` 段修复（`f4b82c2`）
- 移动端响应式 CSS（`768` / `480` 断点）（`0fedbeb`）
- 首次访问引导浮层，localStorage 记忆（`65bd6d8`）
- 空状态文案（库为空 / 404 / 500 页面）（`e753022`）
- 装饰光斑从 4 个减为 1 个（性能）（`5618032`）
- 引入 `prefers-reduced-motion` 媒体查询支持

## 类型说明

- **Security** 任何与安全相关的修改
- **Performance** 影响同步、扫描、渲染性能的修改
- **Architecture** 结构、模块边界、解耦相关的修改
- **Core Features** 用户可见的新功能
- **UX / a11y** 体验、可访问性、移动端适配
- **Deprecated** 即将移除的功能
- **Removed** 已移除的功能
