# Development environment setup

This guide walks through setting up a local development environment for
Armarium on **macOS or Linux** using **Visual Studio Code**. It assumes
you've skimmed the top-level [README.md](../README.md) for a feature
overview.

For the architecture, conventions, and "what to update when" reference, see
[ARCHITECTURE.md](../ARCHITECTURE.md) and [CLAUDE.md](../CLAUDE.md) — these
apply whether you're a human contributor or using
[Claude Code](https://claude.com/claude-code) (see
[Using Claude Code with this repo](#using-claude-code-with-this-repo) below).

To deploy a tagged release instead of setting up a dev environment, see
[DEPLOYMENT.md](DEPLOYMENT.md).

## Prerequisites

- **Git**
- **Python 3.11** (backend)
- **Node.js 20** (frontend)
- **Docker** + **Docker Compose plugin** — optional, for the hot-reload
  Docker setup, running PostgreSQL locally, or building production images
- **Visual Studio Code**

### macOS

```bash
brew install git python@3.11 node@20
brew install --cask visual-studio-code
brew install --cask docker   # or: brew install colima docker docker-compose
```

If you use the standalone `docker-compose` (v2) binary or `colima` instead of
Docker Desktop, make sure the `docker compose` *subcommand* works too —
Homebrew's caveat for `docker-compose` explains adding the plugin directory
to `~/.docker/config.json` (`cliPluginsExtraDirs`) if `docker compose
version` reports "unknown command".

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y git python3.11 python3.11-venv build-essential curl

# Node 20 via nvm (recommended over the distro package, which is often old):
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
\. "$HOME/.nvm/nvm.sh"
nvm install 20

# VS Code: https://code.visualstudio.com/docs/setup/linux
# Docker Engine + Compose plugin: https://docs.docker.com/engine/install/ubuntu/
```

## 1. Clone the repository

```bash
git clone https://github.com/craig530/Armarium.git
cd Armarium
code .
```

## 2. VS Code setup

Open the folder in VS Code (`code .`). A `.vscode/extensions.json` is
included with recommended extensions — VS Code will prompt you to install
them on first open:

- **Python** (`ms-python.python`) + **Pylance** — backend editing/IntelliSense
- **Ruff** (`charliermarsh.ruff`) — inline lint feedback matching `ruff check app`
- **ESLint** (`dbaeumer.vscode-eslint`) — frontend linting
- **Tailwind CSS IntelliSense** (`bradlc.vscode-tailwindcss`)
- **Docker** (`ms-azuretools.vscode-docker`) — optional, for the compose files

Once the backend virtualenv exists (next step), point VS Code at it:
**Cmd/Ctrl+Shift+P → "Python: Select Interpreter" → `backend/.venv/bin/python`**.

## 3. Backend setup

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt   # requirements-dev.txt: test/lint/SAST tools, not in the production image

# Run the dev server with auto-reload
JWT_SECRET=dev ADMIN_PASSWORD=devpass uvicorn app.main:app --reload
```

This starts the API at **http://localhost:8000** (interactive Swagger docs at
`/docs`). On first run it creates `data/armarium.db` — Alembic's
`0001_baseline` migration runs automatically, seeding the default media
subtypes and an `admin` user with the password above.

### Backend tests & quality gates

These mirror CI (`.github/workflows/ci.yml`) and
[ARCHITECTURE.md §7](../ARCHITECTURE.md#7-quality-gates) — run them before
committing backend changes:

```bash
python -m pytest -q   # 119+ tests
ruff check app          # lint
bandit -r app -ll        # SAST — see ARCHITECTURE.md §7 "accepted findings" before adding new # nosec
pip-audit                 # dependency CVEs
```

## 4. Frontend setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev   # → http://localhost:3000 (or next free port), proxies /api etc. to :8000
```

### Frontend tests & quality gates

```bash
npm run build      # production build must succeed
npm test -- --run    # vitest
npm run lint          # eslint
npm audit              # dependency CVEs
```

## 5. Running the full stack with Docker (hot reload)

Instead of steps 3–4, run both services in containers with hot reload:

```bash
cp .env.example .env   # then set JWT_SECRET and ADMIN_PASSWORD
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The `-f` flags are required deliberately, so this override is never loaded in
production. See the root [README.md](../README.md) for `.env` configuration
details.

## 6. Using PostgreSQL locally (optional)

SQLite is the default and primary target (ARCHITECTURE.md §1), but you can
test against PostgreSQL locally:

```bash
docker run -d --name armarium-pg -e POSTGRES_DB=armarium \
  -e POSTGRES_USER=armarium -e POSTGRES_PASSWORD=armarium \
  -p 5432:5432 postgres:16-alpine

DATABASE_URL=postgresql+asyncpg://armarium:armarium@localhost:5432/armarium \
  JWT_SECRET=dev ADMIN_PASSWORD=devpass uvicorn app.main:app --reload
```

CI's `backend-postgres` job runs `backend/scripts/verify_postgres_baseline.py`
against a real `postgres:16-alpine` container on every push — this is the
same check, locally.

## 7. Making schema changes

Schema changes are **Alembic revisions only** (ARCHITECTURE.md §4.3) — there
is no other migration mechanism:

```bash
# after editing app/models/*.py
alembic revision --autogenerate -m "describe the change"
# hand-check the generated migration — especially CHECK/UNIQUE constraints
# and any data backfill/seeding — then:
alembic upgrade head
```

## Using Claude Code with this repo

This repo includes [CLAUDE.md](../CLAUDE.md), which
[Claude Code](https://claude.com/claude-code) reads automatically on
startup and which points to [ARCHITECTURE.md](../ARCHITECTURE.md) for full
conventions. If you have the Claude Code CLI or VS Code/JetBrains extension
installed, no extra setup is needed — open this repo and Claude follows the
same layering, migration, and quality-gate conventions described above
without being asked.

[ARCHITECTURE.md §11](../ARCHITECTURE.md#11-documentation-map) maps which doc
(this one, README, CHANGELOG, DEPLOYMENT.md, THIRD_PARTY_LICENSES.md, ...)
to update for a given kind of change — Claude is instructed to check it
before finishing a task, and human contributors should too.

## Troubleshooting

- **`bcrypt` errors on login** — `passlib` requires `bcrypt==4.0.1` exactly
  (see the comment in `requirements.txt`); newer `bcrypt` releases break
  passlib's internal self-test and crash auth entirely.
- **Frontend port already in use** — Vite falls back to 3001, 3002, ... if
  3000 is busy and prints the port it picked. The backend always binds 8000
  unless you pass `--port` to uvicorn.
- **Can't log in over plain HTTP** — set `COOKIE_SECURE=false` for local
  HTTP-only setups (see the README Configuration table). Leave it `true`
  (the default) behind HTTPS.
- **`docker compose` reports "unknown command"** — see the macOS note above
  about `cliPluginsExtraDirs`, or use the standalone `docker-compose` binary
  as a fallback.
