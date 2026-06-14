# Armarium architecture & principles

This document is the canonical reference for how Armarium is structured and
the conventions to follow when extending it. It's written for both human
contributors and AI assistants (see `CLAUDE.md`, which points here). If a
change would contradict something below, either the change or this document
needs to be updated — keep them in sync.

## 1. Guiding principles

- **Small, self-hosted, single-tenant-ish app.** Armarium is run by one
  household on their own hardware. Favour simplicity and readability over
  enterprise abstractions ("no strict style guide" per `CONTRIBUTING.md`).
- **SQLite first.** PostgreSQL is supported but SQLite is the default and the
  primary target for defaults, migrations and FTS.
- **Defense in depth on the network boundary.** This app is often exposed
  beyond localhost (reverse proxy, Tailscale, etc.). Treat every external
  input — query params, uploaded files, third-party API responses, lookup
  URLs — as untrusted. SSRF/path-traversal/size-limit checks belong at the
  point input enters the system (see §4.6).
- **No dead code, no partial features.** If something is removed, delete it
  completely rather than commenting it out or leaving compatibility shims.
  This was a deliberate decision when retiring the old ad-hoc
  `app/migrations.py` startup-migration functions in favour of Alembic.
- **Tests are the source of truth for behaviour.** 116 backend tests + a
  frontend vitest suite cover the app; any structural change (repository
  refactors, schema changes, etc.) must keep the full suite green.

## 2. Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11), SQLAlchemy 2.0 (async), Alembic |
| Database | SQLite (default, with FTS5 full-text search) or PostgreSQL |
| Frontend | React 18, Vite, Tailwind CSS, Zustand, react-router-dom 6 |
| Auth | JWT (python-jose) + bcrypt via passlib |
| Containerisation | Docker / Docker Compose, non-root multi-stage builds |

## 3. Repository layout

```
backend/
  app/
    main.py            # FastAPI app, middleware, lifespan (migrations/seed/admin)
    config.py          # pydantic-settings Settings, loaded from .env
    database.py        # async engine/session, Base
    models/            # SQLAlchemy ORM models (one file per entity) + enums.py
    schemas/            # Pydantic request/response models (one file per entity)
    repositories/      # Per-model data-access classes (see §4.2)
    api/v1/             # FastAPI routers — one file per resource
    services/           # Business logic that isn't pure CRUD (auth, search,
                         # cover art, external API clients, Plex sync, etc.)
  alembic/             # Migration environment + versions/ (0001_baseline is v1 schema)
  tests/               # pytest suite, one file per router/concern + conftest.py

frontend/
  src/
    api/               # Thin axios wrappers per resource, all go through api/client.js
    store/             # Zustand stores (auth, theme, library filters, reference data)
    components/        # Reusable UI, grouped by feature area (add/, media/, layout/, ui/, ...)
    pages/             # Route-level components (one per page/route)
    lib/               # Pure helper modules (categories, icons, export, etc. — no React)
    hooks/             # Reusable hooks
```

## 4. Backend architecture

### 4.1 Layering

Request flow is strictly layered:

```
router (api/v1/*.py)
  -> repository (repositories/*.py)   — all SQL lives here
  -> models (models/*.py)             — SQLAlchemy ORM
```

with `schemas/*.py` (Pydantic) defining the request/response contracts at the
router boundary, and `services/*.py` for logic that doesn't belong in either
(password hashing, JWT issuance, external API clients, image processing,
search-index maintenance, Plex sync orchestration).

**Routers** are responsible for:
- HTTP concerns: path/query params, status codes, `HTTPException`s
- Permission checks (`Depends(get_current_user)` /
  `Depends(require_permission("can_..."))`)
- Shaping ORM objects into response schemas (`_to_response`/`_build_response`
  helpers)
- File I/O for uploads (covers, icons, logos) via `services/asset_upload.py`

**Repositories** own *all* queries for their model — including aggregate maps
(`item_count_map`), tree-building, lock-reason computation, and bulk
operations. Routers must not construct `select(...)`/`delete(...)` statements
directly; if a router needs a new query, add a method to the relevant
repository.

### 4.2 Repository pattern

Every repository:
- Subclasses `BaseRepository[ModelT]` (`app/repositories/base.py`), which
  provides `get`, `list`, `add`, `delete`, `delete_all`, `commit`, `flush`,
  `refresh`.
- Sets `model = <ORMClass>`.
- Is exposed via a `Depends`-compatible factory function, e.g.:

  ```python
  async def get_location_repository(db: AsyncSession = Depends(get_db)) -> LocationRepository:
      return LocationRepository(db)
  ```

- Adds model-specific methods named for what they return, not how
  (`item_count_map`, `count_by_barcode_or_isbn`, `find_by_name`,
  `locked_map`, `build_tree`), so routers read like a description of the
  endpoint's behaviour.

Current repositories: `MediaItemRepository`, `MediaSubtypeRepository`,
`PlatformRepository`, `LocationRepository`, `UserRepository`,
`PlexConfigRepository`, `PlexLibraryMappingRepository`.

### 4.3 Database & migrations

- Schema is defined once, in the SQLAlchemy models (`app/models/*.py`,
  `Base.metadata`).
- **Alembic is the only schema-change mechanism.** New columns/tables/
  constraints: change the model, then `alembic revision --autogenerate`,
  then hand-check the generated migration (especially `CHECK`/`UNIQUE`
  constraints and any data backfill/seeding).
- `alembic/versions/0001_baseline.py` is the v1 baseline — it creates every
  table with its full v1 constraints and seeds the 10 default media subtypes.
  There is no pre-v1 migration history; this baseline *is* the schema.
- `main.py`'s `lifespan()`:
  - In-memory test DBs (`sqlite+aiosqlite:///:memory:`) skip Alembic and use
    `Base.metadata.create_all` directly — schema-equivalent to the baseline
    by construction, and avoids Alembic seeing a different `:memory:`
    connection than the app's shared `StaticPool` connection.
  - File-based DBs run `alembic upgrade head` against the app's own
    connection via `AsyncConnection.run_sync` (no second engine/event loop).
  - `setup_fts()` (raw SQL FTS5 virtual table + triggers) runs after either
    path — it's SQLite-only and intentionally outside `Base.metadata`.
- `_ensure_admin()` creates the default admin user on first run if no users
  exist, and warns (not errors) if `ADMIN_PASSWORD` is still `"changeme"`.

### 4.4 Auth & permissions

- JWT access tokens (python-jose), bcrypt password hashing (passlib, pinned
  to `bcrypt==4.0.1` — newer bcrypt breaks passlib's self-test, see
  `requirements.txt` comment).
- `services/auth.py`: `get_current_user` (any authenticated user) and
  `require_permission("can_...")` (admins bypass all checks;
  `is_read_only` overrides every `can_*` flag — mirrored client-side by
  `hasPermission()` in `frontend/src/store/index.js`).
- Permission flags are boolean columns on `User` (`can_add_items`,
  `can_manage_locations`, etc.) — add a new flag there, to
  `schemas/user.py`, and to the relevant router's `require_permission(...)`
  call when adding a new gated capability.

### 4.5 Error handling

- `main.py` registers a catch-all `@app.exception_handler(Exception)` that
  logs the full traceback via `logger.exception(...)` and returns a generic
  `{"detail": "Internal server error"}` 500 — never leak tracebacks to
  clients. FastAPI's built-in handlers for `HTTPException` and
  `RequestValidationError` take precedence (more specific exception types),
  so normal 4xx error responses are unaffected.
- Raise `HTTPException` for all expected error conditions (404, 403, 409,
  422). Let unexpected exceptions propagate to the catch-all rather than
  adding broad `try/except` in routers.

### 4.6 External input & SSRF protections

- `services/cover_art._is_safe_url()` rejects URLs resolving to
  private/loopback/link-local/reserved/multicast IPs before the backend
  fetches them — used by both the cover-download pipeline and the
  `/lookup/cover-proxy` endpoint (which proxies third-party cover images for
  the frontend, rate-limited via `SlidingWindowRateLimiter`).
- `services/plex.py` intentionally bypasses `_is_safe_url` for the
  user-configured Plex `base_url` — that's an admin-supplied trusted target,
  not user-controlled input. Any new "fetch a URL the user gave us" feature
  must go through `_is_safe_url` (or an equivalent check) unless it has the
  same "admin-configured trusted host" justification, documented inline.
- File uploads (covers, location icons, platform logos) go through
  `services/asset_upload.py`: content-type allowlist, size limits, and
  filenames derived from content hashes (not user input) to avoid path
  traversal.

### 4.7 Caching & external APIs

- `services/cache.py` provides a simple in-memory TTL cache
  (`lookup_cache`), used by `services/tmdb.py`,
  `services/musicbrainz.py` and `services/openlibrary.py` to avoid
  re-hitting third-party metadata APIs for repeated lookups.
- `hashlib.md5(..., usedforsecurity=False)` is used for non-cryptographic
  purposes only (cache keys, content-addressed filenames) — never for
  passwords or tokens. New non-crypto hash usage should follow the same
  `usedforsecurity=False` convention so bandit doesn't flag it as B324.

## 5. Frontend architecture

### 5.1 State management

Zustand stores in `src/store/index.js`, one slice per concern:
- `useThemeStore` — dark mode, persisted to `localStorage` +
  `<meta name="theme-color">` for PWA chrome.
- `useAuthStore` — JWT + user object, persisted to `localStorage`
  (`armarium-token` / `armarium-user`). `hasPermission(user, flag)` mirrors
  the backend's permission logic and must be kept in sync with
  `services/auth.require_permission` if permission semantics change.
- `useLibraryStore` — view mode + filters for the Library page.
- `useReferenceDataStore` — lazily-loaded, shared cache of
  locations/platforms/media subtypes (`ensureLoaded()` / `invalidate()`).
  Call `invalidate()` after any create/update/delete in the Settings
  managers so the next `ensureLoaded()` picks up the change.

### 5.2 API layer

All HTTP calls go through `src/api/client.js` (axios instance):
- attaches `Authorization: Bearer <token>` from `localStorage`
- formats FastAPI's `{"detail": ...}` error payloads (including 422
  validation-error arrays) into readable `Error` messages
- on 401: clears stored credentials, tells the service worker to drop cached
  `/api/` responses, and redirects to `/login`

Each resource gets a thin wrapper module in `src/api/` (`media.js`,
`locations.js`, etc.) — these are the only files that should import `client`
directly; pages/components call the wrapper functions.

### 5.3 Components & icons

- `src/lib/mediaIcons.js` is the single source of truth for category/subtype
  icons (`CATEGORY_ICONS`, `getSubtypeIcon`). Don't redefine per-category
  icon maps locally in components — import from here.
- `src/lib/categories.js` defines `CATEGORIES`/`SUPERTYPES` (the
  music/films_tv/books × physical/digital taxonomy) — the single source of
  truth for category metadata used by nav, filters, and the add flow.
- `src/lib/navigation.js` holds shared nav-link definitions (`MANAGE_LINKS`)
  used by both the desktop `Navbar` and the mobile `Profile` settings menu.
- UI primitives live in `src/components/ui/` (Button, Modal, Input,
  SelectMenu, Skeleton, Badge, etc.) — prefer these over ad-hoc markup for
  new UI.

### 5.4 Data loading pattern

Pages load data in `useEffect` and call `setState` directly in the effect
body (e.g. `Library.jsx`, `Home.jsx`, `ItemDetail.jsx`, `Admin.jsx`). This is
the established pattern throughout the app — see §7 for the ESLint
configuration note about why the newer "React Compiler readiness" hook rules
are intentionally not enabled. When you *do* need to suppress
`react-hooks/exhaustive-deps` for a deliberately-partial dependency array
(e.g. a debounce effect that must not depend on its own write target), add an
inline comment explaining *why*, then `// eslint-disable-next-line
react-hooks/exhaustive-deps` directly above the dependency array — see
`Library.jsx` for examples.

### 5.5 PWA / offline

`public/sw.js` is a service worker caching `/api/` GET responses for offline
browsing; `OfflineBanner` shows when `navigator.onLine` is false. The auth
client posts `CLEAR_API_CACHE` to the service worker on logout/401 so a new
user on the same device/browser doesn't see cached data from the previous
session.

## 6. Configuration

All runtime config is `pydantic-settings` (`backend/app/config.py`), loaded
from `.env` (see `.env.example`). Settings have safe defaults for local dev;
`JWT_SECRET` auto-generates (with a warning) if unset, and `ADMIN_PASSWORD`
defaults to `"changeme"` (also warned about). Never commit `.env` or any real
secrets/tokens — `.gitignore` already excludes `.env`.

## 7. Quality gates

Run these before committing structural changes:

**Backend** (from `backend/`, with `.venv` activated):
```bash
python -m pytest -q          # full test suite (116 tests)
ruff check app                # lint
bandit -r app -ll              # SAST — see "accepted findings" below
pip-audit                       # dependency CVEs
```

**Frontend** (from `frontend/`):
```bash
npm run build                  # production build must succeed
npm test -- --run               # vitest
npm run lint                     # eslint
npm audit                          # dependency CVEs
```

### Accepted/suppressed findings

- **bandit B608** (3 findings in `app/services/search.py`): low-confidence
  "possible SQL injection" on the FTS5 trigger-creation SQL. The
  interpolated value (`FTS_COLUMNS`) is a fixed module-level constant, not
  user input — a false positive. `# nosec B608` can't be placed on the exact
  flagged line for multi-line triple-quoted f-strings, so there's an
  explanatory comment above instead; don't restructure this code purely to
  satisfy bandit.
- **bandit B105** (`app/main.py`, admin password check): comparing
  `settings.admin_password == "changeme"` to *detect* the unchanged default
  and warn — not a hardcoded credential. Suppressed inline with
  `# nosec B105`.
- **`eslint-plugin-react-hooks` "recommended" config is intentionally not
  used.** v6+ bundles a large family of React Compiler-readiness rules
  (`set-state-in-effect`, `refs`, `static-components`, etc.) that flag the
  effect-based data-loading pattern used throughout this codebase (§5.4).
  Adopting them means rewriting that pattern app-wide, not a lint cleanup.
  `eslint.config.js` enables only `rules-of-hooks` (error) and
  `exhaustive-deps` (warn). Revisit if/when the project adopts React
  Compiler.

## 8. Testing conventions

- Backend: `backend/tests/conftest.py` provides shared fixtures (in-memory
  DB, authenticated clients for admin/regular/read-only users). One test file
  per router/concern (`test_media.py`, `test_locations.py`,
  `test_plex.py`, ...). New endpoints need tests covering: success path,
  permission denial (403), not-found (404), and validation errors (422)
  where relevant.
- Frontend: vitest, colocated `*.test.js`/`*.test.jsx` files
  (`src/lib/reorder.test.js`, `src/hooks/useStepHistory.test.jsx`). Coverage
  is currently light — adding tests for new `lib/` helpers and hooks is
  encouraged.

## 9. Extending the app: adding a new model end-to-end

1. **Model**: `app/models/<name>.py` — SQLAlchemy class, register in
   `app/models/__init__.py`'s `__all__`.
2. **Migration**: `alembic revision --autogenerate -m "add <name>"`, then
   hand-check constraints/seed data.
3. **Schema**: `app/schemas/<name>.py` — `Create`/`Update`/`Response`
   Pydantic models.
4. **Repository**: `app/repositories/<name>.py` — subclass `BaseRepository`,
   add a `get_<name>_repository` factory.
5. **Router**: `app/api/v1/<name>.py` — CRUD endpoints, permission checks,
   register in `app/api/v1/router.py`.
6. **Tests**: `backend/tests/test_<name>.py`.
7. **Frontend**: `src/api/<name>.js` wrapper, store slice if shared state is
   needed, page/component, route in `src/App.jsx`, nav entry if applicable.

## 10. Known tradeoffs & areas for deeper review

These are intentional-for-now decisions or known gaps, not bugs — listed so
future work can revisit them deliberately rather than rediscover them:

- **JWT stored in `localStorage`** (not an `httpOnly` cookie). Simpler for a
  same-origin SPA + API behind a single reverse proxy, but vulnerable to
  token theft via XSS. Revisit if/when the app introduces any
  user-generated-content rendering that isn't strictly sanitised.
- **Frontend major-version upgrades** (React 19, react-router 7, Vite 8,
  Tailwind 4, Zustand 5, lucide-react 1.x) are deliberately *not* bundled
  into routine maintenance — each is a breaking-change migration deserving
  its own PR and manual UI testing pass. Note `npm audit` currently reports
  an esbuild/vite/vitest advisory chain (dev-server-only CORS issue, not
  present in production builds) whose fix requires the Vite 8 jump.
- **Large page/component files** (`Admin.jsx`, `ItemDetail.jsx`,
  `BarcodeScanner.jsx`, `AddFlow.jsx`) mix multiple concerns (several
  settings panels, multiple modals/steps). Splitting these into smaller
  components would improve readability but touches a lot of working code —
  do incrementally, one panel/step at a time, with manual UI verification.
- **No CI workflow** (`.github/workflows/`) currently runs the backend/
  frontend test+lint+build commands from §7 on PRs. Adding one (re-using
  exactly those commands) would catch regressions before merge — good
  first issue for a contributor.
- **Frontend test coverage is light** — only `lib/reorder.js` and
  `hooks/useStepHistory.js` have tests. Page-level tests (Library filters,
  AddFlow steps, Admin panels) would catch regressions from future
  refactors.
