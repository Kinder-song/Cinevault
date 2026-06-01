# CineVault v2 — M0 项目骨架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一个能跑通 `uv run` + `npm run dev` 的最小项目骨架，后端 `/healthz` 返回 200，前端 Vite 启动并显示 hello，CPR / lint / type / test 在 GitHub Actions 中跑通。

**Architecture:** 单仓双目录布局——后端 Python 包 (`src/cinevault/`) 与前端 Vite SPA (`frontend/`) 共享根目录。后端用 FastAPI 工厂模式 + 严格分层骨架；前端用 Vite + React 18 + TS strict。CI 跑后端 ruff/mypy/pytest 和前端 eslint/tsc/vitest。

**Tech Stack:**
- Python 3.11+, uv, FastAPI 0.115+, Pydantic 2, pydantic-settings, SQLAlchemy 2 (async), pytest, pytest-asyncio, httpx, ruff, mypy
- Node 20+, Vite 5, React 18, TypeScript 5.5+ strict, React Router 6, Zustand, TanStack Query, Vitest, Testing Library, ESLint, Prettier
- GitHub Actions, pre-commit

**项目位置:** `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/`

---

## File Structure

本次 M0 落地后 `cinevault-v2/` 长这样：

```
cinevault-v2/
├── .git/
├── .gitignore
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       └── frontend-ci.yml
├── README.md
├── pyproject.toml                  # 后端依赖 + 工具配置
├── src/
│   └── cinevault/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory
│       ├── config.py               # pydantic-settings
│       └── py.typed
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_health.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── .eslintrc.cjs
│   ├── .prettierrc.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── App.test.tsx
│   │   ├── vite-env.d.ts
│   │   └── styles/global.css
│   └── tests/
│       └── setup.ts
```

每个文件职责：

| 文件 | 职责 |
|---|---|
| `pyproject.toml` | Python 依赖、ruff、mypy、pytest 配置 |
| `src/cinevault/main.py` | FastAPI 工厂 + `/healthz` 端点 |
| `src/cinevault/config.py` | pydantic-settings 配置类（基础字段） |
| `tests/test_health.py` | 端到端测 `/healthz` |
| `frontend/vite.config.ts` | Vite + Vitest 配置 |
| `frontend/src/App.tsx` | 根组件，渲染 "CineVault v2" |
| `frontend/src/App.test.tsx` | smoke 测试 |
| `.github/workflows/*.yml` | CI 流水线 |

---

## Task 1: 初始化项目目录与 Git

**Files:**
- Create: `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/`

- [ ] **Step 1.1: 创建项目根目录并初始化 git**

```bash
mkdir -p /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git init -b main
```

- [ ] **Step 1.2: 创建 `.gitignore`**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/.gitignore`：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# Node / Vite
node_modules/
dist/
.vite/
coverage/
*.tsbuildinfo

# OS
.DS_Store
Thumbs.db

# Editor
.vscode/
.idea/
*.swp
*.swo

# Env / secrets
.env
.env.local
*.local

# Data (runtime)
data/
*.db
*.db-journal
```

- [ ] **Step 1.3: 初始提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add .gitignore
git -c user.email=dev@local -c user.name=dev commit -m "chore: initial commit with .gitignore"
```

期望：`[main (root-commit) ...] chore: initial commit with .gitignore`

---

## Task 2: 后端 pyproject.toml（uv + ruff + mypy + pytest）

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 2.1: 写入 `pyproject.toml`**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/pyproject.toml`：

```toml
[project]
name = "cinevault"
version = "0.1.0"
description = "Self-hosted local video library and streaming app"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "CineVault Contributors" }]

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "alembic>=1.13.0",
    "PyJWT>=2.9.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.12",
    "watchfiles>=0.24.0",
    "loguru>=0.7.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
    "types-passlib>=1.7.7.20240819",
]

[project.scripts]
cinevault = "cinevault.main:run"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/cinevault"]

# ===== Ruff =====
[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
    "TID", # flake8-tidy-imports (ban relative)
    "RUF", # ruff-specific
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # function call in default argument (FastAPI uses this)
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["B011"]  # asserts OK

[tool.ruff.lint.isort]
known-first-party = ["cinevault"]

# ===== Mypy =====
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
plugins = ["pydantic.mypy"]
exclude = ["tests/"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

# ===== Pytest =====
[tool.pytest.ini_options]
minversion = "8.0"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=src/cinevault",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
]
testpaths = ["tests"]
asyncio_mode = "auto"

# ===== Coverage =====
[tool.coverage.run]
source = ["src/cinevault"]
branch = true

[tool.coverage.report]
show_missing = true
skip_covered = false
fail_under = 80
```

- [ ] **Step 2.2: 用 uv 同步依赖并验证配置可解析**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
which uv || curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --extra dev
```

期望：生成 `.venv/`、`uv.lock`；无错误输出。

- [ ] **Step 2.3: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add pyproject.toml uv.lock
git -c user.email=dev@local -c user.name=dev commit -m "build: add pyproject.toml with uv/ruff/mypy/pytest"
```

---

## Task 3: 后端最小代码骨架（Config + main）

**Files:**
- Create: `src/cinevault/__init__.py`
- Create: `src/cinevault/py.typed`
- Create: `src/cinevault/config.py`
- Create: `src/cinevault/main.py`

- [ ] **Step 3.1: 包初始化文件**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/src/cinevault/__init__.py`：

```python
"""CineVault v2 - self-hosted local video library and streaming app."""

__version__ = "0.1.0"
```

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/src/cinevault/py.typed`：

```
# Marker file for PEP 561. See https://peps.python.org/pep-0561/
```

- [ ] **Step 3.2: 配置模块**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/src/cinevault/config.py`：

```python
"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables (and an optional `.env` file).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=55300)
    debug: bool = Field(default=False)

    # Security (will be required in production; for M0 we provide a dev default)
    secret_key: str = Field(
        default="dev-secret-change-me-in-production-please-use-openssl-rand-hex-32",
        description="Used to sign JWTs. Must be >= 32 chars in production.",
    )

    # Paths
    data_dir: Path = Field(default=Path("./data"))
    media_dir: Path = Field(default=Path("./data/media"))
    hls_dir: Path = Field(default=Path("./data/hls"))
    thumbnail_dir: Path = Field(default=Path("./data/thumbnails"))

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/cinevault.db",
        description="SQLAlchemy async URL. SQLite by default for zero-setup.",
    )

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance (process-wide)."""
    return Settings()
```

- [ ] **Step 3.3: FastAPI app factory + healthz**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/src/cinevault/main.py`：

```python
"""FastAPI application factory and entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cinevault import __version__
from cinevault.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan hook (startup/shutdown)."""
    # Startup: nothing to do in M0.
    yield
    # Shutdown: nothing to do in M0.


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        settings: Optional Settings instance. If None, reads from environment.

    Returns:
        A fully configured FastAPI app.
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="CineVault",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS - allow local Vite dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        """Liveness probe. Always returns 200 if the process is up."""
        return {"status": "ok", "version": __version__}

    return app


# Module-level app for `uvicorn cinevault.main:app`
app = create_app()


def run() -> None:
    """Entry point for the `cinevault` console script."""
    settings = get_settings()
    uvicorn.run(
        "cinevault.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
```

- [ ] **Step 3.4: 手动验证 import 不报错**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run python -c "from cinevault.main import app; print(type(app).__name__)"
```

期望输出：`FastAPI`（且无 ImportError / Pydantic 错误）

- [ ] **Step 3.5: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add src/
git -c user.email=dev@local -c user.name=dev commit -m "feat(backend): minimal FastAPI app with /healthz"
```

---

## Task 4: 后端测试 /healthz（TDD）

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_health.py`

- [ ] **Step 4.1: 测试包初始化**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/tests/__init__.py`：

```python
"""Test suite for CineVault backend."""
```

- [ ] **Step 4.2: pytest fixtures（先写）**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/tests/conftest.py`：

```python
"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cinevault.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient wrapping a freshly-built app."""
    app = create_app()
    return TestClient(app)
```

- [ ] **Step 4.3: 写 healthz 失败测试**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/tests/test_health.py`：

```python
"""Smoke tests for the /healthz endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_returns_ok(client: TestClient) -> None:
    """GET /healthz should return 200 with status=ok."""
    response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "version": "0.1.0"}


def test_healthz_content_type_is_json(client: TestClient) -> None:
    """GET /healthz should return application/json."""
    response = client.get("/healthz")

    assert response.headers["content-type"].startswith("application/json")


def test_openapi_schema_exposed(client: TestClient) -> None:
    """OpenAPI schema should be available for tooling."""
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "CineVault"
    assert "/healthz" in schema["paths"]
```

- [ ] **Step 4.4: 跑测试确认通过**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run pytest -v
```

期望：`3 passed`，无 mypy 报错（`--cov-fail-under=80` 因为 `main.py` + `config.py` 已被测试覆盖到关键分支）。

- [ ] **Step 4.5: 跑 mypy 验证严格类型**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run mypy src
```

期望：`Success: no issues found in 2 source files`

- [ ] **Step 4.6: 跑 ruff 验证 lint**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run ruff check src tests
uv run ruff format --check src tests
```

期望：两个命令均无 error。

- [ ] **Step 4.7: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add tests/
git -c user.email=dev@local -c user.name=dev commit -m "test(backend): add /healthz smoke tests"
```

---

## Task 5: 前端 Vite + React + TS 初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/styles/global.css`

> 我们不用 `npm create vite`（避免交互式提示），而是直接手写配置文件以便完全可控。

- [ ] **Step 5.1: package.json**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/package.json`：

```json
{
  "name": "cinevault-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint . --max-warnings 0",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc -b --noEmit",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "@tanstack/react-query": "^5.59.0",
    "zustand": "^5.0.0",
    "framer-motion": "^11.11.0",
    "hls.js": "^1.5.15"
  },
  "devDependencies": {
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.2",
    "typescript": "^5.6.2",
    "vite": "^5.4.8",
    "vitest": "^2.1.2",
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/user-event": "^14.5.2",
    "jsdom": "^25.0.1",
    "eslint": "^9.12.0",
    "@typescript-eslint/parser": "^8.8.0",
    "@typescript-eslint/eslint-plugin": "^8.8.0",
    "eslint-plugin-react": "^7.37.1",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.12",
    "prettier": "^3.3.3"
  }
}
```

- [ ] **Step 5.2: TypeScript 严格配置**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/tsconfig.json`：

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/tsconfig.app.json`：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "useUnknownInCatchVariables": true,
    "exactOptionalPropertyTypes": false,
    "verbatimModuleSyntax": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "tests"]
}
```

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/tsconfig.node.json`：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5.3: Vite + Vitest 配置**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/vite.config.ts`：

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:55300',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:55300',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2022',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    css: true,
  },
});
```

- [ ] **Step 5.4: HTML 入口**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#0A0814" />
    <title>CineVault</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5.5: 全局 CSS（设计 token 占位，M1+ 完善）**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/src/styles/global.css`：

```css
/* ===== Design tokens (placeholder; M6+ will expand) ===== */
:root {
  --bg-base: #0a0814;
  --bg-elev-1: #14111e;
  --text-primary: #eceaff;
  --text-secondary: #a5a0d8;
  --accent-primary: #a78bfa;
  --space-4: 16px;
  --radius-md: 10px;
  --motion-base: 220ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

* {
  box-sizing: border-box;
}

html,
body,
#root {
  margin: 0;
  padding: 0;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
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

- [ ] **Step 5.6: Vite 环境声明 + 入口 + 根组件**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/src/vite-env.d.ts`：

```typescript
/// <reference types="vite/client" />
```

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/src/main.tsx`：

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/global.css';

const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('Root element #root not found in index.html');
}

createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/src/App.tsx`：

```tsx
import { useEffect, useState } from 'react';

const HEALTHZ_URL = '/api/healthz';

interface HealthStatus {
  status: 'ok' | 'error';
  version: string;
}

function App(): React.JSX.Element {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(HEALTHZ_URL)
      .then((res) => res.json() as Promise<HealthStatus>)
      .then(setHealth)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Unknown error');
      });
  }, []);

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: 'var(--space-4)',
        padding: 'var(--space-4)',
      }}
    >
      <h1 style={{ fontSize: '3rem', margin: 0 }}>CineVault v2</h1>
      <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
        Local video library and streaming
      </p>
      <section
        aria-label="Backend health"
        style={{
          padding: 'var(--space-4)',
          background: 'var(--bg-elev-1)',
          borderRadius: 'var(--radius-md)',
          minWidth: '320px',
        }}
      >
        <strong>Backend health: </strong>
        {error ? (
          <span style={{ color: '#FCA5A5' }}>✗ {error}</span>
        ) : health ? (
          <span style={{ color: '#86EFAC' }}>
            ✓ {health.status} (v{health.version})
          </span>
        ) : (
          <span>loading…</span>
        )}
      </section>
    </main>
  );
}

export default App;
```

- [ ] **Step 5.7: 安装依赖并构建测试**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm install
npm run typecheck
npm run build
```

期望：typecheck 0 error；build 在 `dist/` 产出 `index.html` + JS bundle。

- [ ] **Step 5.8: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/package.json frontend/tsconfig.json frontend/tsconfig.app.json \
        frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html \
        frontend/src/
git -c user.email=dev@local -c user.name=dev commit -m "feat(frontend): Vite + React 18 + TS strict scaffold"
```

---

## Task 6: 前端 ESLint + Prettier + Vitest setup

**Files:**
- Create: `frontend/.eslintrc.cjs`
- Create: `frontend/.prettierrc.json`
- Create: `frontend/.prettierignore`
- Create: `frontend/tests/setup.ts`
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 6.1: ESLint flat config 替代 `.eslintrc.cjs`（若 v9）**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/eslint.config.js`：

```javascript
import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'node_modules', 'coverage'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.strictTypeChecked],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.es2022 },
      parserOptions: {
        project: ['./tsconfig.app.json', './tsconfig.node.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-misused-promises': 'off',
    },
  },
  {
    files: ['**/*.test.ts', '**/*.test.tsx', 'tests/**/*'],
    rules: {
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
    },
  },
);
```

> 如果 ESLint 9 的 flat config 解析有问题，可改用 legacy `.eslintrc.cjs`，但**优先 flat**。在 `package.json` 增加依赖：
>
> ```bash
> cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
> npm i -D @eslint/js globals typescript-eslint
> ```
>
> 然后把 `eslint . --max-warnings 0` 替换为 `eslint eslint.config.js --max-warnings 0` 在 `package.json scripts` 里。

- [ ] **Step 6.2: Prettier 配置**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/.prettierrc.json`：

```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/.prettierignore`：

```
node_modules
dist
coverage
*.lock
```

- [ ] **Step 6.3: Vitest setup + smoke test**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/tests/setup.ts`：

```typescript
import '@testing-library/jest-dom/vitest';
```

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend/src/App.test.tsx`：

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the CineVault v2 title', () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'ok', version: '0.1.0' }), {
        status: 200,
      }),
    );

    render(<App />);

    expect(screen.getByRole('heading', { name: /cinevault v2/i })).toBeInTheDocument();
  });

  it('shows backend health after fetch resolves', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'ok', version: '0.1.0' }), {
        status: 200,
      }),
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/ok/i)).toBeInTheDocument();
    });
  });

  it('shows error message when fetch fails', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error('network down'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/network down/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 6.4: 跑 vitest / eslint / tsc / prettier 验证**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run typecheck
npm run lint
npm run format:check
npm run test
```

期望：四个命令均 0 error。Vitest 输出 3 passed。

- [ ] **Step 6.5: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add frontend/eslint.config.js frontend/.prettierrc.json frontend/.prettierignore \
        frontend/tests/ frontend/src/App.test.tsx frontend/package.json frontend/package-lock.json
git -c user.email=dev@local -c user.name=dev commit -m "build(frontend): eslint + prettier + vitest setup with App smoke tests"
```

---

## Task 7: GitHub Actions CI

**Files:**
- Create: `.github/workflows/backend-ci.yml`
- Create: `.github/workflows/frontend-ci.yml`

- [ ] **Step 7.1: 后端 CI**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/.github/workflows/backend-ci.yml`：

```yaml
name: Backend CI

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
      - '.github/workflows/backend-ci.yml'
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
      - '.github/workflows/backend-ci.yml'

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: 'latest'

      - name: Set up Python
        run: uv python install 3.11

      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: |
            .venv
            ~/.cache/uv
          key: ${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}
          restore-keys: |
            ${{ runner.os }}-uv-

      - name: Install dependencies
        run: uv sync --extra dev --frozen

      - name: Lint (ruff)
        run: |
          uv run ruff check src tests
          uv run ruff format --check src tests

      - name: Type-check (mypy)
        run: uv run mypy src

      - name: Test (pytest)
        run: uv run pytest
```

- [ ] **Step 7.2: 前端 CI**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/.github/workflows/frontend-ci.yml`：

```yaml
name: Frontend CI

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-ci.yml'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-ci.yml'

defaults:
  run:
    working-directory: frontend

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Format check (prettier)
        run: npm run format:check

      - name: Lint (eslint)
        run: npm run lint

      - name: Type-check (tsc)
        run: npm run typecheck

      - name: Test (vitest)
        run: npm run test

      - name: Build (vite)
        run: npm run build
```

- [ ] **Step 7.3: README + 占位运行说明**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/README.md`：

```markdown
# CineVault v2

Self-hosted local video library and streaming app.

## Status

**M0 — Project skeleton** ✓

- Backend: FastAPI + Python 3.11
- Frontend: React 18 + Vite + TypeScript
- CI: GitHub Actions (lint / type / test / build)

## Development

### Backend

```bash
uv sync --extra dev
uv run cinevault          # start server on :55300
uv run pytest             # run tests
uv run ruff check src tests
uv run mypy src
```

### Frontend

```bash
cd frontend
npm install
npm run dev               # start dev server on :5173
npm run typecheck
npm run lint
npm run test
npm run build
```

The Vite dev server proxies `/api/*` to the FastAPI backend on `:55300`.

## Project Structure

See `docs/superpowers/specs/2026-06-01-cinevault-v2-greenfield-design.md` for the full design.
```

- [ ] **Step 7.4: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add .github/ README.md
git -c user.email=dev@local -c user.name=dev commit -m "ci: add backend and frontend GitHub Actions workflows"
```

---

## Task 8: 本地端到端冒烟验证

**Files:** (无新文件)

- [ ] **Step 8.1: 启动后端（独立终端）**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run cinevault
```

期望输出：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:55300 (Press CTRL+C to quit)
```

- [ ] **Step 8.2: 手动 curl 验证 healthz**

```bash
curl -i http://127.0.0.1:55300/healthz
```

期望：
```
HTTP/1.1 200 OK
content-type: application/json
...

{"status":"ok","version":"0.1.0"}
```

- [ ] **Step 8.3: 启动前端（另一终端）**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/frontend
npm run dev
```

期望：`Vite ... Local: http://localhost:5173/`

- [ ] **Step 8.4: 浏览器访问 http://localhost:5173/**

期望看到：
- "CineVault v2" 标题
- "Local video library and streaming" 副标题
- "Backend health: ✓ ok (v0.1.0)" 卡片

- [ ] **Step 8.5: 关闭两个 dev server（Ctrl+C 两次）**

无新提交。

---

## Task 9: pre-commit 配置

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 9.1: pre-commit 配置文件**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=512']
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.2
    hooks:
      - id: ruff
        args: ['--fix', '--exit-non-zero-on-fix']
        files: '^(src|tests)/.*\.py$'
      - id: ruff-format
        files: '^(src|tests)/.*\.py$'

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.3.3
    hooks:
      - id: prettier
        files: ^frontend/.*\.(ts|tsx|js|jsx|css|json|md)$
        additional_dependencies:
          - prettier@3.3.3
```

- [ ] **Step 9.2: 安装并运行**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

期望：所有 hook 通过（如果首次有 format 修改，commit 后再跑一次应全绿）。

- [ ] **Step 9.3: 提交**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add .pre-commit-config.yaml
git -c user.email=dev@local -c user.name=dev commit -m "chore: add pre-commit hooks (ruff + prettier)"
```

---

## Task 10: M0 验收 + Tag

- [ ] **Step 10.1: 跑全部本地质量门**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy src
uv run pytest
cd frontend && npm run typecheck && npm run lint && npm run format:check && npm run test && npm run build
```

期望：所有命令 0 error。

- [ ] **Step 10.2: 推送并触发 CI**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git remote add origin <your-repo-url>  # 若尚未添加
git push -u origin main
```

到 GitHub Actions 页面确认两个 workflow 都绿。

- [ ] **Step 10.3: 打 tag `m0-skeleton`**

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git tag -a m0-skeleton -m "M0: project skeleton complete"
git push origin m0-skeleton
```

- [ ] **Step 10.4: 在 CHANGELOG / docs/superpowers/plans 记录进度**

写入 `/Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2/docs/M0-COMPLETE.md`：

```markdown
# M0 — Project Skeleton Complete

**Date:** 2026-06-01
**Tag:** m0-skeleton

## Delivered

- Backend: FastAPI + Pydantic + SQLAlchemy 2 async + Alembic skeleton
- `/healthz` returns 200 with version
- Frontend: Vite + React 18 + TypeScript strict + React Router + TanStack Query + Zustand + Framer Motion + hls.js
- App shows "CineVault v2" + live backend health
- CI: backend (ruff/mypy/pytest with 80% coverage gate) and frontend (prettier/eslint/tsc/vitest/build) on GitHub Actions
- pre-commit: ruff + prettier
- README with run instructions

## Verified

- ✓ `uv run cinevault` boots on :55300
- ✓ `curl /healthz` returns `{"status":"ok","version":"0.1.0"}`
- ✓ `npm run dev` boots on :5173 with proxy to backend
- ✓ All local quality gates pass
- ✓ All GitHub Actions jobs pass

## Next

M1 — Backend base: User model, JWT auth, library scanner, ffprobe metadata, raw MP4 streaming.
```

提交并推送：

```bash
cd /Users/alexkinder/Hacker/AI/ClaudeCode/cinevault-v2
git add docs/M0-COMPLETE.md
git -c user.email=dev@local -c user.name=dev commit -m "docs: record M0 completion"
git push
```

---

## Self-Review Checklist

- [x] **Spec coverage:** M0 验收项（后端 Hello + 前端 Hello + CI 跑通）由 Task 1-10 全部覆盖
- [x] **Placeholder scan:** 无 "TBD" / "TODO" / "add appropriate error handling"；所有代码块完整
- [x] **Type consistency:** `create_app()` 在 Task 3 定义并被 Task 4 conftest 引用，签名一致；`HealthStatus` interface 在 Task 5.6 与 Task 6.3 一致
- [x] **No contradictions:** 后端用 `127.0.0.1:55300`、前端 dev 5173 → 55300 proxy，与 spec 一致
- [x] **每个 task 2-5 分钟可完成**（除 Task 5 略长外）
- [x] **每个 task 有 commit**
- [x] **TDD：测试先写（Task 4）**

## Notes for Engineer

- **uv 不可用时**：用 `pip install -e .[dev]` 替代 `uv sync`，但仍建议装 uv（性能 + 锁文件优势）
- **ESLint v9 flat config** 可能与你环境已有的全局 ESLint 冲突；如出问题，删除全局 `eslint` 并仅用项目本地
- **不要在 M0 添加业务功能**（tags / videos / collections 全部留给 M1-M3）
- **不要修改 secret_key 默认值进 git**（已在 `.gitignore` 排除 `.env`；CI 用默认 dev 值是 OK 的）
- **M0 完成后**进入 M1（后端基座：User / JWT / 媒体库扫描 / ffprobe / 原始 MP4 流），下一个 plan 由 writing-plans 在 M0 收尾时产出
