#!/usr/bin/env python3
"""Build the downloadable DIVU AI application package.

    python scripts/build_download_package.py

Produces ``frontend/public/downloads/divu-ai-app.zip`` — a complete, runnable copy of the
platform (frontend + backend + docs + launchers), served from the website's download page.

Excluded: git history, virtualenvs, node_modules, build output, local databases and caches.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "frontend" / "public" / "downloads" / "divu-ai-app.zip"
ROOT_NAME = "divu-ai"

EXCLUDED_DIRS = {
    ".git",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".data",
    "downloads",
    "coverage",
    "htmlcov",
}

EXCLUDED_FILES = {
    ".env",
    "tsconfig.tsbuildinfo",
    ".coverage",
    "divu.db",
}

INCLUDED_TOP_LEVEL_FILES = [
    "LICENSE",
    "Makefile",
    "docker-compose.yml",
    ".env.example",
    "README.md",
]

INCLUDED_DIRS = ["backend", "frontend", "docs", "scripts"]

START_SH = r"""#!/usr/bin/env bash
# DIVU AI — one-command launcher (macOS / Linux)
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
NODE_BIN="${NODE_BIN:-node}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.11+ is required. Set PYTHON_BIN if it is named differently." >&2
  exit 1
fi
if ! command -v "$NODE_BIN" >/dev/null 2>&1; then
  echo "Node.js 22+ is required." >&2
  exit 1
fi

echo "==> Preparing the backend virtual environment"
if [ ! -d backend/.venv ]; then
  "$PYTHON_BIN" -m venv backend/.venv
fi
backend/.venv/bin/pip install --quiet --upgrade pip
backend/.venv/bin/pip install --quiet -r backend/requirements-dev.txt

echo "==> Preparing the database"
[ -f .env ] || cp .env.example .env
mkdir -p backend/.data
(cd backend && ../backend/.venv/bin/python manage.py db-upgrade || true)
(cd backend && ../backend/.venv/bin/python manage.py seed || true)

echo "==> Installing frontend dependencies"
(cd frontend && npm install --no-audit --no-fund)

cleanup() {
  echo "==> Stopping DIVU AI"
  [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
  [ -n "${WEB_PID:-}" ] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting the API on http://localhost:${API_PORT}"
(cd backend && ../backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}") &
API_PID=$!

echo "==> Starting the web app on http://localhost:${WEB_PORT}"
(cd frontend && API_PROXY_TARGET="http://127.0.0.1:${API_PORT}" npx next dev --hostname 0.0.0.0 --port "${WEB_PORT}") &
WEB_PID=$!

echo ""
echo "DIVU AI is running."
echo "  Web app : http://localhost:${WEB_PORT}"
echo "  API docs: http://localhost:${API_PORT}/docs"
echo "  Demo    : demo@divu.ai / Demo!Passphrase1"
echo "Press Ctrl+C to stop."
wait
"""

START_BAT = r"""@echo off
REM DIVU AI - one-command launcher (Windows)
setlocal
cd /d "%~dp0"

set API_PORT=8000
set WEB_PORT=3000

where py >nul 2>nul && (set PYTHON_BIN=py) || (set PYTHON_BIN=python)

echo ==^> Preparing the backend virtual environment
if not exist "backend\.venv" (
  %PYTHON_BIN% -m venv backend\.venv
)
backend\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements-dev.txt

echo ==^> Preparing the database
if not exist ".env" copy /Y ".env.example" ".env" >nul
if not exist "backend\.data" mkdir "backend\.data"
pushd backend
..\.venv\Scripts\python.exe manage.py db-upgrade
..\.venv\Scripts\python.exe manage.py seed
popd

echo ==^> Installing frontend dependencies
pushd frontend
call npm install --no-audit --no-fund
popd

echo ==^> Starting DIVU AI
echo    Web app : http://localhost:%WEB_PORT%
echo    API docs: http://localhost:%API_PORT%/docs
echo    Demo    : demo@divu.ai / Demo!Passphrase1

start "DIVU AI API" cmd /c "cd /d %~dp0backend && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %API_PORT%"
start "DIVU AI Web" cmd /c "cd /d %~dp0frontend && set API_PROXY_TARGET=http://127.0.0.1:%API_PORT%&& npx next dev --hostname 0.0.0.0 --port %WEB_PORT%"

echo.
echo Two new windows were opened. Close them to stop DIVU AI.
endlocal
"""

README_INSTALL = r"""# DIVU AI — runnable application package

**DIVU AI** · Created by **DIVYESH BAMBHANIYA** (Founder & Creator) ·
*Beyond Conversations. Towards Intelligence.*

This zip is a complete copy of the platform: Next.js frontend, FastAPI backend, database
migrations, automated tests, documentation and one-command launchers.

---

## Quick start

Requirements: **Python 3.11+** and **Node.js 22+**.

```bash
unzip divu-ai-app.zip
cd divu-ai
./start.sh          # Windows: start.bat
```

Then open:

* Web app → http://localhost:3000
* API docs → http://localhost:8000/docs
* Demo login → `demo@divu.ai` / `Demo!Passphrase1`

The launcher creates a virtualenv, installs dependencies, applies migrations, seeds the demo
data and starts both servers. Press `Ctrl+C` to stop.

Prefer to run the pieces yourself?

```bash
# Terminal 1 — API
cd backend && ../backend/.venv/bin/python manage.py run --host 0.0.0.0 --port 8000

# Terminal 2 — web
cd frontend && API_PROXY_TARGET=http://127.0.0.1:8000 npx next dev --port 3000
```

## Install it on your home screen

The web app is a progressive web app (PWA):

* **Android / Windows / ChromeOS** — open the site and use **Install app**, or the "Add to home
  screen" button on the Install page.
* **iOS** — Safari → **Share** → **Add to Home Screen**.
* It opens in a standalone window and caches the app shell, so it launches even while offline.

## What is inside

| Path | Contents |
|---|---|
| `backend/` | FastAPI app, Alembic migrations, 62-test pytest suite, `manage.py` CLI |
| `frontend/` | Next.js 15 app, PWA manifest, service worker, generated icon set |
| `docs/` | Architecture, API, database schema, security, deployment, roadmap, phase reports |
| `Makefile` | `setup`, `dev-backend`, `dev-frontend`, `test`, `lint`, `migrate`, `seed` |
| `docker-compose.yml` | PostgreSQL+pgvector, Redis, MinIO, API and web containers |
| `.env.example` | Every configuration variable (no secrets) |

### Useful commands

```bash
make test            # run the backend test suite (SQLite — no services needed)
make lint            # ruff + TypeScript
make check-config    # validate configuration, never prints secrets
make migrate         # alembic upgrade head
make seed            # create roles + demo user
make create-admin e=you@example.com
```

### Docker stack (PostgreSQL + pgvector, Redis, MinIO)

```bash
cp .env.example .env
docker compose up --build
```

## Status of the platform

Phase 1 (foundation) is complete and tested; Phase 2 (frontend and installable app) is in
progress. Chat, model routing, memory, RAG, agents, tools, the Developer Studio and add-ons are
planned phases 3-9 — see `docs/DEVELOPMENT_ROADMAP.md`. Nothing in this package pretends to be
finished: each phase report lists what works and what does not.

## Security notes

* No secrets are shipped. Generate `DIVU_SECRET_KEY` and `DIVU_ENCRYPTION_KEY` before any
  non-local deployment (see `docs/SECURITY_GUIDE.md`).
* `start.sh` / `start.bat` are for local use: they create a demo user and use SQLite.
* Set `DIVU_APP_ENV=production` to enable the startup guards (strong secrets required, debug and
  public registration refused).

## License

MIT — see `LICENSE`.
"""


def should_skip(path: Path, relative: Path) -> bool:
    parts = set(relative.parts)
    if parts & EXCLUDED_DIRS:
        return True
    if path.name in EXCLUDED_FILES:
        return True
    if path.name.endswith((".pyc", ".pyo", ".log")):
        return True
    return False


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        TARGET.unlink()

    file_count = 0
    with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in INCLUDED_TOP_LEVEL_FILES:
            source = ROOT / name
            if source.exists():
                archive.write(source, f"{ROOT_NAME}/{name}")
                file_count += 1

        for directory in INCLUDED_DIRS:
            base = ROOT / directory
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if path.is_dir():
                    continue
                relative = path.relative_to(ROOT)
                if should_skip(path, relative):
                    continue
                archive.write(path, f"{ROOT_NAME}/{relative.as_posix()}")
                file_count += 1

        archive.writestr(f"{ROOT_NAME}/start.sh", START_SH)
        archive.writestr(f"{ROOT_NAME}/start.bat", START_BAT)
        archive.writestr(f"{ROOT_NAME}/README-INSTALL.md", README_INSTALL)
        file_count += 3

    size_mb = TARGET.stat().st_size / (1024 * 1024)
    print(f"wrote {TARGET} ({file_count} files, {size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
