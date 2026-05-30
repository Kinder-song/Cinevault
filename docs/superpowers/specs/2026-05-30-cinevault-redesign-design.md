# CineVault 设计规范 v1.0

## 项目概述

CineVault 是一个自托管的个人本地视频媒体中心，支持多用户、视频流媒体、缩略图生成、标签管理和收藏夹功能。

**目标：** 将 CineVault 打造成用户使用体验极佳、Web页面美观度极高、代码质量优秀的优质项目。

---

## 一、设计语言（Design Language）

### 1.1 视觉方向

| 模式 | 风格 | 关键词 |
|------|------|--------|
| **Light Mode** | 现代极简梦幻马卡龙 | 柔和粉彩、大量留白、呼吸感、玻璃拟态、轻盈动效 |
| **Dark Mode** | 影院沉浸梦幻紫罗兰 | 深邃暗色、霓虹泡泡漂浮、玻璃拟态叠加、沉浸式观影 |

### 1.2 色彩系统

#### Light Mode（现代极简梦幻马卡龙）

```css
:root {
  /* 背景色 */
  --bg-primary: #FDF4F8;       /* 奶油粉白 - 主背景 */
  --bg-secondary: #FFFFFF;      /* 纯白 - 卡片背景 */
  --bg-glass: rgba(255, 255, 255, 0.75);
  --bg-muted: #FDF2F8;          /* 米粉 - 次级背景 */

  /* 文字色 */
  --text-primary: #831843;      /* 深玫瑰色 - 主文字 */
  --text-secondary: #64748B;    /* 灰蓝色 - 次级文字 */
  --text-muted: #9CA3AF;        /* 淡灰 - 辅助文字 */

  /* 强调色 - 马卡龙调色板 */
  --accent-pink: #EC4899;      /* 马卡龙粉 */
  --accent-lavender: #A78BFA;   /* 淡紫色 */
  --accent-sky: #7DD3FC;        /* 天空蓝 */
  --accent-mint: #86EFAC;       /* 薄荷绿 */
  --accent-peach: #FDBA74;      /* 蜜桃色 */

  /* 功能色 */
  --color-success: #86EFAC;
  --color-warning: #FCD34D;
  --color-error: #FCA5A5;
  --color-info: #7DD3FC;

  /* 边框与阴影 */
  --border-primary: #FBCFE8;    /* 粉边框 */
  --border-secondary: #E9D5FF;  /* 紫边框 */
  --shadow-color: rgba(236, 72, 153, 0.08);
  --shadow-lg: 0 10px 40px rgba(236, 72, 153, 0.12);

  /* 圆角 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-xl: 28px;
}
```

#### Dark Mode（影院沉浸梦幻紫罗兰）

```css
:root[data-theme="dark"] {
  /* 背景色 */
  --bg-primary: #0D0B14;        /* 深紫黑 - 主背景 */
  --bg-secondary: #151220;      /* 暗紫灰 - 卡片背景 */
  --bg-glass: rgba(30, 27, 75, 0.65);
  --bg-muted: #1E1B4B;           /* 深紫 - 次级背景 */

  /* 文字色 */
  --text-primary: #F5F3FF;      /* 淡紫白 - 主文字 */
  --text-secondary: #A5B4FC;     /* 柔紫 - 次级文字 */
  --text-muted: #6366F1;        /* 靛蓝 - 辅助文字 */

  /* 强调色 - 霓虹调色板 */
  --accent-pink: #F472B6;       /* 霓虹粉 */
  --accent-purple: #C084FC;     /* 紫罗兰 */
  --accent-cyan: #67E8F9;       /* 青色光晕 */
  --accent-violet: #818CF8;      /* 紫光 */
  --accent-magenta: #F0ABFC;    /* 品红 */

  /* 功能色 */
  --color-success: #86EFAC;
  --color-warning: #FCD34D;
  --color-error: #F87171;
  --color-info: #67E8F9;

  /* 边框与阴影 */
  --border-primary: rgba(139, 92, 246, 0.25);
  --border-secondary: rgba(192, 132, 252, 0.2);
  --glow-pink: 0 0 30px rgba(244, 114, 182, 0.3);
  --glow-purple: 0 0 40px rgba(192, 132, 252, 0.25);

  /* 圆角 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
}
```

### 1.3 字体系统

```css
/* Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Nunito:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  /* 字体族 */
  --font-display: 'Outfit', system-ui, sans-serif;
  --font-body: 'Nunito', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* 字号 */
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */
  --text-4xl: 2.25rem;    /* 36px */

  /* 行高 */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;
}
```

### 1.4 动效系统

```css
:root {
  /* 动画时长 */
  --duration-instant: 50ms;
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --duration-slower: 400ms;

  /* 缓动函数 */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

  /* Ambient Blobs (Dark Mode Only) */
  --blob-1: radial-gradient(ellipse at 20% 30%, rgba(192, 132, 252, 0.15) 0%, transparent 50%);
  --blob-2: radial-gradient(ellipse at 80% 20%, rgba(244, 114, 182, 0.12) 0%, transparent 50%);
  --blob-3: radial-gradient(ellipse at 50% 80%, rgba(103, 232, 249, 0.1) 0%, transparent 50%);
}

/* Ambient Blob 动画 */
@keyframes blob-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -20px) scale(1.05); }
  50% { transform: translate(-20px, 30px) scale(0.95); }
  75% { transform: translate(-30px, -10px) scale(1.02); }
}

@keyframes blob-drift {
  0% { transform: translate(0, 0); }
  33% { transform: translate(40px, 20px); }
  66% { transform: translate(-30px, 40px); }
  100% { transform: translate(0, 0); }
}

/* 淡入上移动画 */
@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 缩放淡入动画 */
@keyframes scale-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
```

### 1.5 间距系统

```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;       /* 16px */
  --space-5: 1.25rem;    /* 20px */
  --space-6: 1.5rem;     /* 24px */
  --space-8: 2rem;       /* 32px */
  --space-10: 2.5rem;    /* 40px */
  --space-12: 3rem;      /* 48px */
  --space-16: 4rem;      /* 64px */
  --space-20: 5rem;      /* 80px */
}
```

### 1.6 阴影系统

```css
:root {
  /* Light Mode 阴影 */
  --shadow-sm: 0 1px 2px rgba(236, 72, 153, 0.05);
  --shadow-md: 0 4px 6px rgba(236, 72, 153, 0.07);
  --shadow-lg: 0 10px 15px rgba(236, 72, 153, 0.1);
  --shadow-xl: 0 20px 25px rgba(236, 72, 153, 0.15);

  /* 玻璃态阴影 */
  --shadow-glass: 0 8px 32px rgba(0, 0, 0, 0.08);
}

:root[data-theme="dark"] {
  /* Dark Mode 阴影与光晕 */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
  --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.6);
  --shadow-glow-pink: 0 0 30px rgba(244, 114, 182, 0.25);
  --shadow-glow-purple: 0 0 30px rgba(192, 132, 252, 0.2);
}
```

---

## 二、UI组件规范（Component Specifications）

### 2.1 按钮（Buttons）

#### 主要按钮
```css
.btn-primary {
  background: linear-gradient(135deg, var(--accent-pink) 0%, var(--accent-lavender) 100%);
  color: white;
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--text-sm);
  min-height: 44px;
  min-width: 44px;
  transition: all var(--duration-normal) var(--ease-out);
  box-shadow: var(--shadow-md);
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}
.btn-primary:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}
```

#### 次要按钮
```css
.btn-secondary {
  background: transparent;
  color: var(--accent-pink);
  border: 2px solid var(--border-primary);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-weight: 500;
  min-height: 44px;
  transition: all var(--duration-normal) var(--ease-out);
}
.btn-secondary:hover {
  background: var(--bg-muted);
  border-color: var(--accent-pink);
}
```

#### 图标按钮
```css
.btn-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
}
.btn-icon:hover {
  background: var(--bg-muted);
}
.btn-icon:active {
  transform: scale(0.95);
}
```

### 2.2 卡片（Cards）

#### 视频卡片
```css
.video-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-out);
  backdrop-filter: blur(20px);
}
.video-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--accent-pink);
}
.video-card:active {
  transform: translateY(-2px);
}
```

#### 玻璃态卡片
```css
.glass-card {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
}
```

### 2.3 输入框（Inputs）

```css
.input {
  background: var(--bg-secondary);
  border: 2px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-base);
  min-height: 48px;
  transition: all var(--duration-fast) var(--ease-out);
}
.input:focus {
  outline: none;
  border-color: var(--accent-pink);
  box-shadow: 0 0 0 4px rgba(236, 72, 153, 0.1);
}
.input::placeholder {
  color: var(--text-muted);
}
```

### 2.4 徽章/标签（Badges/Tags）

```css
.tag {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-xl);
  font-size: var(--text-xs);
  font-weight: 500;
  background: var(--bg-muted);
  color: var(--text-secondary);
  transition: all var(--duration-fast) var(--ease-out);
}
.tag:hover {
  background: var(--accent-pink);
  color: white;
}
```

### 2.5 导航栏（Navbar）

```css
.navbar {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-primary);
  height: 64px;
  padding: 0 var(--space-6);
}
```

### 2.6 Toast 通知

```css
.toast {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  box-shadow: var(--shadow-lg);
  animation: fade-in-up var(--duration-slow) var(--ease-out);
}
.toast-success { border-left: 4px solid var(--color-success); }
.toast-error { border-left: 4px solid var(--color-error); }
.toast-warning { border-left: 4px solid var(--color-warning); }
.toast-info { border-left: 4px solid var(--color-info); }
```

---

## 三、页面布局规范（Page Layouts）

### 3.1 响应式断点

```css
/* Mobile First */
--breakpoint-sm: 640px;   /* 手机横屏 */
--breakpoint-md: 768px;   /* 平板竖屏 */
--breakpoint-lg: 1024px;  /* 平板横屏 / 小笔记本 */
--breakpoint-xl: 1280px;  /* 桌面 */
--breakpoint-2xl: 1536px; /* 大屏 */
```

### 3.2 栅格系统

```css
.grid {
  display: grid;
  gap: var(--space-6);
}
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.grid-cols-6 { grid-template-columns: repeat(6, minmax(0, 1fr)); }

@media (max-width: 768px) {
  .grid-cols-2, .grid-cols-3, .grid-cols-4, .grid-cols-6 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 480px) {
  .grid-cols-2, .grid-cols-3, .grid-cols-4, .grid-cols-6 {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
```

### 3.3 容器宽度

```css
.container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}
.container-narrow { max-width: 960px; }
.container-medium { max-width: 1200px; }
```

---

## 四、页面专项设计

### 4.1 首页（Video Gallery）

- 顶部：搜索栏 + 视图切换 + 排序选项
- 中部：Bento 网格布局展示视频卡片
- 卡片元素：缩略图、标题、时长、进度条、标签、收藏图标
- 分页：底部居中分页器

### 4.2 视频播放页（Video Player）

- 顶部：返回按钮 + 视频标题
- 主体：视频播放器（支持全屏、画中画）
- 底部：集数信息、标签操作、收藏、分享
- 侧栏（元数据）：分辨率、编码、帧率、文件大小
- Theater Mode：播放器扩展至全宽

### 4.3 仪表盘（Dashboard）

- 顶部：欢迎语 + 统计数据卡片（总视频数、总时长、总大小、收藏数、已观看时长）
- 中部：图表区域（标签分布、编码格式、分辨率分布）
- 所有数据基于当前用户

### 4.4 设置页（Settings）

- 头像/用户名显示区
- 表单：用户名、视频路径、高级设置
- 保存/重置按钮

### 4.5 登录页（Login）

- 居中卡片表单
- Logo + 应用名称
- 用户名/密码输入框 + 登录按钮
- 错误提示区域

---

## 五、安全规范（Security）

### 5.1 身份验证

- 所有 API 路由需要 `@login_required` 装饰器
- Session 必须在登录成功后调用 `session.regenerate_id()`
- 使用 bcrypt 密码哈希（自动使用 gensalt）

### 5.2 输入验证

- 所有用户输入必须验证
- 路径参数必须通过 `validate_video_path()` 验证
- 数据库查询必须使用参数化查询

### 5.3 错误响应

- 错误信息不得暴露内部细节
- 统一错误响应格式：
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "用户友好的错误描述"
  }
}
```

### 5.4 速率限制

- 登录接口实现 `LoginAttemptTracker`
- 5次失败后锁定300秒

---

## 六、性能规范（Performance）

### 6.1 前端性能

- 图片懒加载 `loading="lazy"`
- 预留图片宽高防止 CLS
- 使用 CSS 变量实现主题切换
- 动画使用 `transform` 和 `opacity`
- 搜索防抖 100ms

### 6.2 后端性能

- MySQL 连接池（8连接）
- Waitress WSGI 服务器（8线程，2MB缓冲）
- 增量同步（基于文件 mtime/size）
- 缩略图缓存

### 6.3 数据库优化

- 添加必要索引：
```sql
CREATE INDEX idx_videos_filename ON videos(filename);
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_created ON videos(created_at);
CREATE INDEX idx_video_tags_video ON video_tags(video_id);
CREATE INDEX idx_video_tags_tag ON video_tags(tag_id);
CREATE INDEX idx_collections_user ON collections(user_id);
```

---

## 七、代码质量规范

### 7.1 错误处理

```python
# 标准错误响应
from utils.exceptions import APIError

@user_bp.errorhandler(APIError)
def handle_api_error(e):
    return jsonify({
        "success": False,
        "error": {
            "code": e.code,
            "message": e.message
        }
    }), e.status_code
```

### 7.2 日志规范

```python
# 结构化日志格式
{
    "timestamp": "ISO8601",
    "level": "INFO/WARNING/ERROR",
    "request_id": "uuid",
    "user_id": 1,
    "action": "video.play",
    "duration_ms": 150
}
```

### 7.3 命名规范

- Python: snake_case
- JavaScript: camelCase（变量/函数），PascalCase（类/组件）
- CSS: kebab-case
- 数据库表: snake_case（单数名词）

---

## 八、实施计划

### Phase 1: UI 美观度升级（当前阶段）
1. 更新 CSS 变量系统（Light + Dark）
2. 更新字体系统（Outfit + Nunito）
3. 重构 CSS 样式（组件化）
4. 添加动效（Ambient Blobs、过渡动画）
5. 更新模板（base.html、index.html、video.html、dashboard.html）

### Phase 2: 播放器体验优化
1. 增强播放器控件 UI
2. 优化字幕显示
3. 添加键盘快捷键提示
4. 改进截图灯箱

### Phase 3: 管理功能增强
1. 改进搜索算法（模糊搜索）
2. 增强标签系统（颜色选择、自动补全）
3. 收藏夹拖拽排序
4. 批量操作

### Phase 4: 移动端优化
1. 响应式布局完善
2. 触控优化
3. 底部导航栏

### Phase 5: 安全与健壮性
1. 修复 CRITICAL/HIGH 问题
2. 添加数据库索引
3. 统一错误处理
4. CSRF 保护
5. Session 安全加固

---

## 九、已知问题修复清单

### CRITICAL（必须立即修复）
- [ ] 硬编码默认密码 admin123
- [ ] 缺失 file_mtime 列导致同步失效
- [ ] XSS 漏洞（截图灯箱）
- [ ] 默认 SECRET_KEY

### HIGH
- [ ] Session fixation（登录后未 regenerate_id）
- [ ] 缺少 CSRF 保护
- [ ] 登录接口无限速率
- [ ] 缺少数据库索引
- [ ] Dashboard stats 缺少 user_id 过滤

### MEDIUM
- [ ] 错误响应不一致
- [ ] 重复 login_required 装饰器
- [ ] 资源泄漏（文件句柄）
- [ ] Magic numbers

---

## 十、验收标准

- [ ] Light Mode 和 Dark Mode 均可用且美观
- [ ] 主题切换流畅无闪烁
- [ ] 所有交互有适当动效反馈
- [ ] 移动端响应正常
- [ ] 无 CRITICAL 安全问题
- [ ] 代码结构清晰易维护
- [ ] 单元测试覆盖核心功能