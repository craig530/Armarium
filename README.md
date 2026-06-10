# Armarium

A self-hosted media catalogue for CDs, DVDs, Blu-rays and Books.

**Features:** barcode scanning via device camera · automatic cover art · OpenLibrary / MusicBrainz / TMDB metadata · hierarchical physical location tracking · JWT auth with multi-user + admin role · CSV/JSON export & import · PWA (add to iOS/Android home screen) · offline browsing · dark mode · keyboard shortcuts

---

## Quick start

### Ubuntu Server — first deploy

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# 2. Clone into the standard location
mkdir -p ~/docker
git clone https://github.com/craig530/Armarium ~/docker/Armarium
cd ~/docker/Armarium

# 3. Configure
cp .env.example .env
nano .env   # set JWT_SECRET and ADMIN_PASSWORD (both required)

# 4. Start
docker compose up -d

# 5. Open  http://<server-ip>:8080
```

### macOS (Docker Desktop)

```bash
git clone https://github.com/craig530/Armarium armarium && cd armarium
cp .env.example .env && nano .env   # set JWT_SECRET and ADMIN_PASSWORD
docker compose up -d
open http://localhost:8080
```

### macOS — local dev (no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
JWT_SECRET=dev ADMIN_PASSWORD=devpass uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

### Docker development (hot reload)

```bash
# Uses docker-compose.dev.yml — does NOT auto-load in production
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Updates & automatic deployment

The server is set up so that Armarium lives at `~/docker/Armarium` alongside other stacks.
A nightly cron job already running on the server handles updates automatically:

```cron
# Runs nightly — pulls latest images and restarts all stacks in ~/docker/
* 2 * * * find ~/docker -name docker-compose.yml -execdir docker compose pull \; -execdir docker compose up -d \;
```

**To ship a change:** push to the `main` branch on GitHub. The cron will pick it up overnight. For an immediate deploy, SSH into the server and run:

```bash
cd ~/docker/Armarium && git pull && docker compose up -d --build
```

---

## Configuration

All configuration is in `.env` at the project root. **Never commit `.env` to git** — it is listed in `.gitignore`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `JWT_SECRET` | **yes** | — | Random hex string. Generate: `openssl rand -hex 32` |
| `ADMIN_PASSWORD` | **yes** | — | Initial admin account password |
| `PORT` | no | `8080` | Host port for the web UI |
| `ADMIN_USERNAME` | no | `admin` | Initial admin account username |
| `JWT_EXPIRE_MINUTES` | no | `10080` (7 days) | Session length |
| `TMDB_API_KEY` | no | — | Required for DVD/Blu-ray metadata. Free key at tmdb.org |
| `DATABASE_URL` | no | SQLite | See PostgreSQL section below |

Generate a JWT secret:

```bash
openssl rand -hex 32
```

---

## First login

On first startup the admin account is created automatically using the values from `.env`.
Log in at `http://<host>:8080/login`, then visit **user menu → Admin panel** to create additional users.

---

## TMDB API key

DVD and Blu-ray metadata is powered by [TMDB](https://www.themoviedb.org/).
Books (OpenLibrary) and CDs (MusicBrainz) work without any key.

1. Create a free account at https://www.themoviedb.org/signup
2. Go to **Settings → API → Request an API key → Developer**
3. Add to `.env`: `TMDB_API_KEY=your_key_here`
4. `docker compose restart backend`

---

## API documentation

Interactive Swagger UI is available while the app is running:

```
http://localhost:8080/api/docs
http://localhost:8000/docs   (direct, if backend port is exposed)
```

All endpoints require a Bearer token obtained from `POST /api/v1/auth/login`.

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `/` | Focus search |
| `n` | Go to Add Item |
| `g` | Grid view |
| `l` | List view |
| `Esc` | Go back |

---

## PWA / Add to home screen

On iOS Safari: **Share → Add to Home Screen**. On Android: browser menu → **Install app**.

> Service workers require HTTPS in production. Terminate TLS at your reverse proxy (Caddy, Traefik, nginx) before Armarium.

---

## Export / import

**Export:** user menu → Export CSV or Export JSON (all users can export).

**Import** (admin only) via the API:

```bash
# Get a token first
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' | jq -r .access_token)

# Import a CSV
curl -X POST "http://localhost:8080/api/v1/library/import?format=csv" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@my-library.csv"
```

CSV column headers must match the export format. Column order does not matter.

---

## Manual backup

From the **Admin panel → Backup now**, or via API:

```bash
curl -s -X POST http://localhost:8080/api/v1/library/backup \
  -H "Authorization: Bearer $TOKEN"
```

Backups are stored in the `app_data` volume under `data/backups/`. The 30 most recent are kept automatically.

**Full volume snapshot:**

```bash
docker run --rm -v armarium_app_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/armarium-$(date +%Y%m%d).tar.gz /data
```

---

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

---

## Architecture

```
armarium/
├── backend/              FastAPI + SQLAlchemy async + SQLite
│   ├── app/
│   │   ├── api/v1/       auth, users, media, locations, lookup, export/import
│   │   ├── models/       User, MediaItem, Location
│   │   ├── schemas/      Pydantic schemas
│   │   └── services/     JWT/bcrypt auth, lookup APIs, cover art + resize, TTL cache
│   └── tests/            pytest smoke tests
├── frontend/             React 18 + Vite + Tailwind CSS
│   ├── src/
│   │   ├── api/          Axios client with Bearer token injection + 401 redirect
│   │   ├── components/   UI, layout, media cards, barcode scanner, add flow, locations
│   │   ├── pages/        Library, AddItem, ItemDetail, Locations, Admin, Login
│   │   ├── hooks/        useKeyboardShortcuts
│   │   └── store/        Zustand — auth, theme, library UI state
│   └── public/           manifest.json, sw.js (offline service worker), favicon
├── docker-compose.yml    Production: backend + nginx/frontend (port 8080)
├── docker-compose.dev.yml Dev: hot-reload backend + Vite dev server (explicit -f flag)
└── .env.example          Template — copy to .env and fill in before running
```

---

## Switching to PostgreSQL

1. Add a `db` service to `docker-compose.yml`:

```yaml
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: armarium
      POSTGRES_USER: armarium
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U armarium"]
      interval: 10s
      retries: 5

volumes:
  pg_data:
```

2. Add `asyncpg` to `backend/requirements.txt`.

3. Set in `.env`:

```
DATABASE_URL=postgresql+asyncpg://armarium:changeme@db:5432/armarium
```

4. Make `backend` depend on `db`: `condition: service_healthy`.

5. `docker compose up -d --build`
