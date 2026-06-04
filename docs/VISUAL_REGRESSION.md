# 视觉回归测试指南

> 5 计划重构（Plan 1–5）后的 UI 视觉验证清单。
> 任何非琐碎的 UI 改动后都应跑一遍本文档的截图流程。
> 一次完整流程约 10 分钟。

## 概述

本文档定义 6 张关键页面截图 + 1 个移动端变体，用于在重构后人工核对 UI 是否符合预期。

**为什么需要这份指南：**
- 重构涉及安全、性能、架构、评论、a11y 5 个维度，模板与 CSS 都有改动
- 视觉退化（错位、丢失样式、玻璃拟态失效）不会触发任何自动化测试
- 截图是最低成本的可视化回归基线

**什么时候跑：**
- 每次 PR 修改了 `templates/`、`static/css/` 或 `static/js/` 中的视觉相关模块
- Plan 5 的 a11y 改动（键盘可达、灯箱、响应式）尤其需要截图核对
- 重大版本（v0.x → v0.y）发布前必跑

## 前置条件

| 项 | 要求 |
|---|---|
| Python | 3.10+ |
| MySQL | 8.0+，已建好 `video` 库 |
| 浏览器 | Chrome 120+（其他 Chromium 内核亦可） |
| 视口 | 桌面 1280×800；移动端 390×844（iPhone 12） |
| 视频数据 | `./video/` 目录里至少 **5 个** 视频文件（保证网格不空） |
| 观看历史 | 至少观看过 1 个视频（保证首页"最近观看"轨道非空） |
| 截图 | 至少 1 个视频已有 `screenshots/*.jpg`（保证灯箱可点开） |

### 启动应用

```bash
# 1. 装依赖
pip install -r requirements.txt

# 2. 启动
python3 app.py
# 等待控制台输出 "Running on http://0.0.0.0:55300"

# 3. 浏览器打开
open http://localhost:55300
```

### 准备数据（首次跑）

如果数据库是空的：

```bash
# 1. 登录 admin / admin123
# 2. 系统会强制跳转改密页 —— 改成新密码
# 3. 把视频文件拷到 ./video/
# 4. 访问 / 触发自动同步（首屏可能要等 5-10 秒）
# 5. 进入任意视频播放 30 秒以上 —— 产生"最近观看"记录
# 6. 若无截图，进入视频页后等 5-10 秒（后台 worker 会生成）
```

### 浏览器设置

- **登录状态**：以 `admin` 登录，保持登录
- **缩放**：100%（Ctrl+0 / Cmd+0 重置）
- **扩展**：建议在隐身窗口中跑，避免广告拦截器影响
- **缓存**：截 404 前 Ctrl+Shift+R 硬刷一次

---

## 截图清单

> 截图存放位置：`docs/screenshots/`
> 命名规范：`NN-<name>.png`（NN 为两位序号）

### 1. 登录页 — `01-login.png`

| 项 | 内容 |
|---|---|
| **URL** | http://localhost:55300/login |
| **前置操作** | 已登录则先 `GET /logout` |
| **登录账号** | `admin` / `admin123`（或改密后的密码） |

**应看到的元素：**
- [ ] 居中、玻璃拟态（`backdrop-filter: blur()`）的卡片，**最大宽度 ~420px**
- [ ] 顶部大字标题 **"CineVault"**（渐变填充，粉 → 淡紫）
- [ ] 副标题 **"您的私人视频档案库"**
- [ ] 用户名输入框（带浮动 label "用户名"）
- [ ] 密码输入框（带浮动 label "密码"）
- [ ] **"登录"** 按钮（圆角胶囊形，粉 → 紫渐变背景）
- [ ] 背景至少 1 个**柔光球**（`glow-orb`）装饰
- [ ] 顶部无导航栏（`{% block nav %}{% endblock %}` 留空）
- [ ] **不应有**：404 字样、推荐视频、视频网格

### 2. 首页（视频库）— `02-home.png`

| 项 | 内容 |
|---|---|
| **URL** | http://localhost:55300/ |
| **前置操作** | 以 admin 登录；保证 ≥5 个视频已同步 |
| **视口** | 1280×800 |

**应看到的元素：**
- [ ] 顶部 **Navbar**：左侧 "CineVault" 标题，右侧图标（搜索 / 历史 / 仪表盘 / 设置 / 登出）
- [ ] **"最近观看"** 横向轨道（带 `history` 图标 + 章节标题）
  - 卡片为 16:9 缩略图 + 标题，**横向滚动**而非网格
  - 若无观看历史，整段隐藏（不显示空标题）
- [ ] **Filter Bar**（横向，玻璃拟态）：
  - 左侧搜索框（带 `search` 放大镜图标 + 占位符"搜索视频、标签、元数据..."）
  - 右侧两个 `<select>`：合集过滤（"全部合集"）+ 排序（按名称 / 大小 / 日期）
  - 网格/列表切换按钮（`grid-3x3` 与 `list` 图标）
- [ ] **视频网格**（桌面 2-4 列自适应）：
  - 卡片为 `<a>` 元素，hover 时阴影变深、轻微上浮
  - 卡片含：缩略图（16:9）、标题、`分辨率` / `fps` / `码率` 角标、tag 胶囊
- [ ] 加载完成时右上角应有 toast 提示"同步完成"

### 3. 视频页（播放 + 元数据）— `03-video.png`

| 项 | 内容 |
|---|---|
| **URL** | http://localhost:55300/video/`<your-file.mp4>` |
| **前置操作** | 在首页点击任一视频卡片进入 |
| **视口** | 1280×800 |

**应看到的元素（自上而下）：**
- [ ] 顶部 Navbar（同首页）
- [ ] **HTML5 视频播放器**（16:9，自定义控件条）
  - 控件条含：播放/暂停、当前时间/总时长、进度条（含已缓冲段）、音量、静音、画中画、影院模式、全屏
  - 视频右上角可能浮 "离线" / "错误" 覆盖层（如有则是 OK 的）
- [ ] **视频标题** + 元数据行（时长 · 大小 · 分辨率 · 帧率 · 码率）
- [ ] **标签胶囊行**（多色，可点击筛选）
- [ ] **操作按钮**：`收藏` / `评分 ★`（5 星）/ `分享` / `刷新封面`（admin 限定）
- [ ] **"字幕"** 章节（如有 `.srt` / `.vtt` / `.ass`）
- [ ] **"截图 (N)"** 章节：横向滚动的小缩略图（点击会打开灯箱）
- [ ] **"视频封面"** 章节：单张大图
- [ ] **评论区**（页底，默认可能显示"还没有评论，快来发表第一条吧"）

### 4. 评论区 — `04-comments.png`

| 项 | 内容 |
|---|---|
| **URL** | 同上视频页 |
| **前置操作** | 滚动到页底评论区，**先发一条测试评论** |

**测试评论输入**（验证 XSS 防护）：
```
测试 <script>alert('XSS')</script> 与 "引号" 与 '单引号'
```

**应看到的元素：**
- [ ] 评论**输入区**（`<textarea>` + `maxlength=2000` + "发表" 按钮）
- [ ] 字符计数器（输入超过限制时变红）
- [ ] 评论**列表**，每条含：用户名、时间戳（"刚刚" / "5 分钟前"）、内容、删除按钮（自己的评论可见）
- [ ] 你刚发的那条**应作为纯文本**显示（`<script>` 标签应被渲染为字面字符，**不**弹窗）
- [ ] 提交后输入框清空、列表立即刷新出新评论（无需整页 reload）

**XSS 验证清单：**
- [ ] 浏览器 DevTools Console **无 `alert` 调用**
- [ ] 右键 → 查看源码，搜索 `<script>alert` —— 应**仅**出现在你刚发的内容里，但被转义为 `&lt;script&gt;`

### 5. 截图灯箱（Lightbox）— `05-lightbox.png`

| 项 | 内容 |
|---|---|
| **URL** | 同上视频页 |
| **前置操作** | 滚动到"截图 (N)"章节，**点击任一缩略图** |
| **注意** | 截图前 Esc 键**不要**按下去 |

**应看到的元素：**
- [ ] **全屏深色遮罩**（`background: rgba(0,0,0,0.85)` 左右）
- [ ] 居中显示的截图，**保持原比例**（不拉伸）
- [ ] 右上角 **关闭按钮（X）**，玻璃拟态圆形按钮
- [ ] 遮罩层级最高（`z-index` 高于 navbar 与播放器）

**功能验证（截图前手动测一次）：**
- [ ] 按 **Esc** 键 → 灯箱关闭
- [ ] 点击图片**外侧**（遮罩区域）→ 灯箱关闭
- [ ] 点击图片**本身** → 不关闭（仅关闭按钮 / Esc / 外侧点击）

**a11y 验证：**
- [ ] DevTools → Elements → 找到 `<div role="dialog" aria-modal="true">` 节点
- [ ] Tab 键焦点能落到关闭按钮

### 6. 404 错误页 — `06-404.png`

| 项 | 内容 |
|---|---|
| **URL** | http://localhost:55300/nonexistent-path-xyz |
| **前置操作** | 直接在地址栏输入任意不存在的路径 |

**应看到的元素：**
- [ ] 巨大渐变字 **"404"**（粉 → 紫渐变填充）
- [ ] 错误文案 **"找不到这个视频了"**（注意：模板里**没有** emoji）
- [ ] **"回到首页"** 链接（带 `home` 图标）
- [ ] 顶部 Navbar 仍存在
- [ ] 背景至少 1 个柔光球

**不应有：**
- [ ] 任何 Python traceback、SQL 错误、堆栈信息（已通过 `utils/errors.py` 净化）
- [ ] 500 状态码（404 才是正确响应）

### 7. 移动端（首页）— `07-mobile-home.png`

| 项 | 内容 |
|---|---|
| **URL** | http://localhost:55300/ |
| **前置操作** | Chrome DevTools → 切换设备工具栏（`Cmd+Shift+M` / `Ctrl+Shift+M`）→ 选 **"iPhone 12 Pro"**（390×844） |
| **视口** | 390 × 844 |

**应看到的元素：**
- [ ] Navbar **折叠**：标题缩小、右侧图标可能改为汉堡菜单或隐藏次要项
- [ ] **"最近观看"** 轨道**仍水平滚动**（不变成垂直列表）
- [ ] **视频网格降为 2 列**（768px 断点）；480px 以下进一步降为 **1 列**
- [ ] Filter Bar：搜索框、select 全部存在，但**合集 / 排序**可能折行
- [ ] 视频卡片：标题字号缩小、tag 胶囊可能换行
- [ ] **不应有横向滚动条**（页面宽度 ≤ 视口宽度）

**断点测试：**
- [ ] 在 DevTools 顶栏把宽度从 390 拖到 768 → 应看到网格从 1 列变 2 列
- [ ] 拖到 1024 → 变 3-4 列
- [ ] 拖到 1280 → 桌面布局

---

## 验证清单

跑完所有截图后填这张表。每行打勾或写问题。

| # | 截图 | 文件 | 通过 | 备注 |
|---|------|------|------|------|
| 1 | 登录页 | `01-login.png` | ☐ | |
| 2 | 首页 | `02-home.png` | ☐ | |
| 3 | 视频页 | `03-video.png` | ☐ | |
| 4 | 评论区 | `04-comments.png` | ☐ | |
| 5 | 灯箱 | `05-lightbox.png` | ☐ | |
| 6 | 404 | `06-404.png` | ☐ | |
| 7 | 移动端 | `07-mobile-home.png` | ☐ | |

**整体通过条件：** 7/7 全部勾选；视觉与本文档"应看到"列表一致。

**如有失败项：**
1. 在"备注"列写具体差异（例：第 3 项的"刷新封面"按钮位置错位 20px）
2. 截图保留为 `<NN>-<name>-FAIL.png`，方便 PR review 时 diff
3. 若是重构引入的回归 → 阻断 PR；若是浏览器/数据问题 → 重新跑一次

---

## 保存与提交

### 目录准备

```bash
mkdir -p docs/screenshots
touch docs/screenshots/.gitkeep   # 跟踪空目录
```

### 命名建议

Chrome 截图默认保存到 `~/Downloads/`，建议重命名后 move 进 `docs/screenshots/`：

```bash
# 桌面（截图 1-6）
mv ~/Downloads/Screenshot*.png docs/screenshots/01-login.png
mv ~/Downloads/Screenshot*.png docs/screenshots/02-home.png
# ...

# 移动端
mv ~/Downloads/Screenshot*.png docs/screenshots/07-mobile-home.png
```

### Chrome 截图快捷键

| 平台 | 可见视口 | 整页（含滚动外） | 选中元素 |
|---|---|---|---|
| macOS | `Cmd+Shift+4` → 空格 → 点击窗口 | DevTools → ⋮ → Capture full size screenshot | DevTools → 右键元素 → Capture node screenshot |
| Windows / Linux | `Ctrl+Shift+S`（Snipping Tool） | 同上 | 同上 |

> 整页截图（full size）能完整记录长内容（视频页、评论区），但要注意视口统一在 1280×800。

### 提交到 git

```bash
git add docs/screenshots/
git status                              # 确认 .gitkeep 和 7 张图都在
git commit -m "docs(visual): capture post-refactor UI screenshots

7 baseline screenshots (6 desktop + 1 mobile) verified
against the 5-plan refactor visual checklist."
git push
```

`.gitkeep` 应当**保留** —— 即便后续 `docs/screenshots/` 有图，`.gitkeep` 也无害。

### 截图体积优化

单张 PNG 截图 200-800KB 不等。提交前可选压缩：

```bash
# macOS
brew install imageoptim
imageoptim docs/screenshots/*.png

# Linux
sudo apt install optipng
optipng -o2 docs/screenshots/*.png
```

---

## 未来：自动化截图

当前**不**实现，但 CI 接入时可考虑：

| 工具 | 优势 | 接入成本 |
|---|---|---|
| [Playwright](https://playwright.dev/) | 跨浏览器（Chromium / Firefox / WebKit）、`expect(page).toHaveScreenshot()` 内建视觉回归 | ~50 行 JS |
| [puppeteer](https://pptr.dev/) | Chrome-only、API 简洁、npm 生态丰富 | ~30 行 JS |
| [backstopjs](https://garris.github.io/BackstopJS/) | 专为视觉回归设计、内建 diff 与阈值 | 配置文件驱动 |

最小可行 Playwright 草图（仅供参考）：

```js
// scripts/screenshots.mjs
import { chromium, devices } from 'playwright';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:55300/login');
  await page.screenshot({ path: 'docs/screenshots/01-login.png' });
  // ... 重复 6 张
  await page.setViewportSize(devices['iPhone 12 Pro'].viewport);
  await page.goto('http://localhost:55300/');
  await page.screenshot({ path: 'docs/screenshots/07-mobile-home.png' });
  await browser.close();
})();
```

**当前选择手动的原因：**
- 重构已收尾，7 张截图各跑一次足够建立基线
- 引入 Playwright 需加 100+ MB 依赖到 `devDependencies`，对当前小项目过重
- 手动跑一次 ~10 分钟，比调脚本快

---

## 相关文件

- 重构日志：[`CHANGELOG.md`](../CHANGELOG.md)
- 模板列表：[`templates/`](../templates/)（11 个 Jinja 模板）
- CSS 模块：[`static/css/`](../static/css/)（`tokens` / `glass` / `cards` / `player` / `comments`）
- 启动入口：[`app.py`](../app.py)
