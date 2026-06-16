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
- **Tests are the source of truth for behaviour.** 200 backend tests + a
  frontend vitest suite cover the app; any structural change (repository
  refactors, schema changes, etc.) must keep the full suite green.

## 2. Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11), SQLAlchemy 2.0 (async), Alembic, APScheduler 3.10 |
| Database | SQLite (default, with FTS5 full-text search) or PostgreSQL |
| Frontend | React 19, Vite 8, Tailwind CSS 4, Zustand 5, react-router-dom 7 |
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
`PlatformRepository`, `LocationRepository`, `ItemListRepository`,
`UserRepository`, `PlexConfigRepository`, `PlexLibraryMappingRepository`,
`ScheduledJobRepository`.

`LocationRepository.descendant_ids(location_id)` returns that location's id
plus every id nested beneath it (BFS over the parent→children map built from
`flat_rows()`). `GET /media?location_id=` resolves this set and passes it to
`MediaItemRepository.search(location_ids=...)`, so filtering by a parent
location also matches items stored in its descendant locations. Similarly,
`GET /media?list_id=` joins `media_item_lists` and filters to items linked to
that `ItemList`, via `MediaItemRepository.search(list_id=...)`.

**Many-to-many relationships** follow the pattern established by
`ItemList`/`media_item_lists` (`app/models/item_list.py`) — the first M2M in
the codebase. The association table is a plain `Table(...)` (not a mapped
class) alongside the "many" side's model, with `ondelete="CASCADE"` on both
FKs. `MediaItem.lists = relationship("ItemList", secondary=media_item_lists,
lazy="selectin")` is one-directional — no `back_populates`, since `ItemList`
doesn't need an `.items` collection (item counts are computed via
`ItemListRepository.item_count_map()`, a `GROUP BY` over the association
table, mirroring `PlatformRepository.item_count_map`). Membership is set via
`MediaItemRepository.set_item_lists(item, list_ids, category)`, which
validates every id exists and belongs to the item's category before replacing
`item.lists` wholesale — follow the same validate-then-replace approach for
any new M2M where one side is category- or type-scoped. CRUD on `ItemList`
itself is gated by the `can_manage_lists` permission flag (mirrors
`can_manage_locations`/`can_manage_platforms`); `GET /lists` only requires
`get_current_user`, since all users need it for filtering.

`MediaItemRepository.auto_link_item(item, subtype)`, run after creating an
item, links it to other items of the same category that are clearly the same
title. Primary match is an exact `AUTO_LINK_FIELD` comparison
(`tmdb_id`/`musicbrainz_id`/`isbn`/`igdb_id`, by category) — a strong enough
signal to link regardless of other metadata. If that finds nothing (e.g. a
Plex-synced item with no `musicbrainz_id`), it falls back to a same-category
title+year match, filtered through `_editions_compatible()` so an explicit
`edition` mismatch (e.g. "Remastered" vs "Anniversary Edition") doesn't
produce a false-positive link.

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
- **Shared Postgres enum types (`mediacategory`, `supertype`) — use
  `postgresql.ENUM(..., create_type=False)`, not `sa.Enum(...,
  create_type=False)`.** The generic `sa.Enum`'s `create_type` flag is
  silently dropped when SQLAlchemy adapts it to Postgres's native `ENUM`
  during DDL, so `sa.Enum(..., create_type=False)` still attempts (and
  fails with `DuplicateObjectError`) `CREATE TYPE` whenever a migration
  referencing that enum runs in an Alembic invocation where an earlier
  migration already created the type in a *previously committed*
  transaction (i.e. any upgrade of an existing deployment — a fresh-DB CI
  run masks this because the type-creating and type-reusing migrations run
  in one transaction). `0003_add_media_lists.py` uses
  `sqlalchemy.dialects.postgresql.ENUM(..., create_type=False)`, which
  correctly suppresses `CREATE TYPE` regardless of transaction history —
  follow that pattern for any new table referencing `mediacategory` or
  `supertype`. (`0001_baseline.py`'s own `plex_library_mappings.category`
  and the FTS-setup `sa.column(...)` enum refs use the ineffective
  `sa.Enum(..., create_type=False)` form too, but are harmless there since
  they run in the same transaction as the type's creation — left as-is since
  editing an already-applied migration is out of scope.)
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
- Dual-mode token transport: `POST /auth/login` both returns
  `access_token` in the body (for API clients — see README import/backup
  examples, sent as `Authorization: Bearer <token>`) and sets it as an
  `httpOnly`, `SameSite=Lax`, `Secure` (unless `COOKIE_SECURE=false`) cookie
  named `access_token` — this is what the browser SPA relies on.
  `POST /auth/logout` clears the cookie. `services/auth.get_current_user`
  checks the `Authorization` header first, then falls back to the cookie
  (`ACCESS_TOKEN_COOKIE_NAME`).
- `services/auth.py`: `get_current_user` (any authenticated user) and
  `require_permission("can_...")` (admins bypass all checks;
  `is_read_only` overrides every `can_*` flag — mirrored client-side by
  `hasPermission()` in `frontend/src/store/index.js`).
- Permission flags are boolean columns on `User` (`can_add_items`,
  `can_manage_locations`, `can_manage_schedules`, etc.) — add a new flag
  there, to `schemas/user.py`, and to `api/v1/users.py`'s create/update
  handlers, and to the relevant router's `require_permission(...)` call when
  adding a new gated capability. `can_manage_schedules` is special: Plex sync
  schedule mutations check it inline via `_require_can_manage_schedules`
  (not `require_permission`) because admins bypass it regardless.

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
  (`lookup_cache`), used by `services/tmdb.py`, `services/musicbrainz.py`,
  `services/openlibrary.py`, and `services/igdb.py` to avoid
  re-hitting third-party metadata APIs for repeated lookups.
- **IGDB** (`services/igdb.py`) uses Twitch OAuth2: `IGDB_CLIENT_ID` +
  `IGDB_CLIENT_SECRET` → `POST id.twitch.tv/oauth2/token` → bearer token
  cached in-process (~60-day TTL, refreshed on expiry via `asyncio.Lock`).
  Queries are `POST api.igdb.com/v4/games` with a Lisp-like body syntax.
  Barcode lookup uses `external_games.category = 10` (EAN/UPC category in
  IGDB's schema). When credentials are absent, the endpoint returns 503.
  Attribution logo at `frontend/src/assets/igdb/logo.svg` (CC BY-SA 4.0
  from Wikimedia Commons), displayed via `IGDBAttribution.jsx` mirroring
  `TMDBAttribution.jsx`.
- TMDB has no barcode lookup of its own. `GET /lookup/barcode/{barcode}` for
  a films_tv (or unspecified-category) barcode that MusicBrainz didn't
  resolve falls back to `services/upc.lookup_films_tv_by_barcode()`: looks
  the barcode up on UPCitemdb's free trial endpoint
  (`api.upcitemdb.com/prod/trial/lookup`, fixed host, no API key — same SSRF
  posture as the other providers), strips bracketed format/region tags from
  the returned product title (`_clean_title()`), and searches TMDB by the
  cleaned title via `tmdb.search_titles()`.
- `hashlib.md5(..., usedforsecurity=False)` is used for non-cryptographic
  purposes only (cache keys, content-addressed filenames) — never for
  passwords or tokens. New non-crypto hash usage should follow the same
  `usedforsecurity=False` convention so bandit doesn't flag it as B324.
- **Cover fallback chains**, scoped to single-item lookups (barcode/ISBN
  scan) rather than multi-result `search_*` (which would multiply HTTP calls
  10-20x):
  - TMDB: `_cover_image_url()` prefers `poster_path`, falling back to
    `backdrop_path` (free — same API response). Used by both single-item
    detail lookups and `search_titles`.
  - MusicBrainz (`lookup_by_barcode`): HEAD-probes the release-level Cover
    Art Archive URL and, on a miss, falls back to the release-group's front
    cover (`coverartarchive.org/release-group/{id}/front-250`).
  - Open Library (`lookup_by_isbn`): if neither Open Library's own
    `cover.large/medium/small` yields a cover, falls back to Google Books
    (`/books/v1/volumes?q=isbn:...`, no API key) for
    `imageLinks.thumbnail`/`smallThumbnail`.
- `MediaItem.tmdb_rating` (nullable `Float`) stores TMDB's `vote_average`,
  returned by `get_movie_details`/`get_tv_details` and shown as "TMDB Rating"
  on Films & TV item detail pages. `MediaItem.user_rating` (nullable
  `Integer`, CHECK-constrained to 1-5) is the user's personal star rating,
  settable on any item via the `StarRating` component.

### 4.8 Scheduled jobs (APScheduler)

Recurring background tasks (Plex sync, library maintenance, backups) are
managed by `services/scheduler.py`, which wraps an APScheduler
`AsyncIOScheduler`:

- **Persistence** — job configs are stored in the `scheduled_jobs` table
  (`app/models/scheduled_job.py`: `job_type`, `target_id`, `interval_hours`,
  `auto_remove_stale`, `export_base_dir`, `last_run_at/status/created/updated/removed/error`).
  APScheduler's built-in SQLAlchemy job store is intentionally NOT used — it
  serialises via pickle, a security concern. Instead, on startup
  `scheduler_service.start(db)` reads all rows from `scheduled_jobs` and
  registers them with APScheduler via `_register(job)`. The DB table and
  APScheduler are kept in sync by the CRUD endpoints.
- **Test isolation** — the scheduler is NOT started for in-memory test DBs
  (checked via `settings.database_url.endswith(":memory:")`). `_register`,
  `remove`, and `next_run_time` all no-op if `scheduler.running is False`.
- **Dispatcher** (`_dispatch(scheduled_job_id)`) — single entry point for all
  jobs: reads config in a fresh session, runs the appropriate handler, and
  persists the result. `export_covers` is skipped (without updating
  `last_run_at`) if it already ran today — once-per-day enforcement.
- **Admin maintenance jobs** (`ADMIN_JOB_TYPES: auto_link, redownload_covers,
  purge_covers, export_covers, backup`) — managed via `GET/POST/DELETE
  /api/v1/admin/schedules/{job_type}` (admin only).
- **Plex sync schedules** — managed via `GET/POST/DELETE
  /api/v1/admin/plex/mappings/{id}/schedule`. Create/delete requires
  `can_manage_schedules` or admin; GET requires only `can_add_items`.
- **Plex delta sync efficiency** — on re-syncing an existing item, covers are
  not re-downloaded (`_apply_cover` is only called for newly-created items).
  The `updated` counter only increments when a metadata field actually changed;
  items that exist with identical data show as processed but not updated.

## 5. Frontend architecture

### 5.1 State management

Zustand stores in `src/store/index.js`, one slice per concern:
- `useThemeStore` — dark mode, persisted to `localStorage` +
  `<meta name="theme-color">` for PWA chrome.
- `useAuthStore` — the access token itself lives in an `httpOnly` cookie the
  frontend never reads; only the user profile is cached, in `localStorage`
  (`armarium-user`), for an optimistic initial render before `refreshUser()`
  (called on every `Layout` mount) confirms the cookie against `/auth/me`.
  `hasPermission(user, flag)` mirrors the backend's permission logic and must
  be kept in sync with `services/auth.require_permission` if permission
  semantics change.
- `useLibraryStore` — view mode + filters for the Library page.
- `useReferenceDataStore` — lazily-loaded, shared cache of
  locations/platforms/media subtypes/lists (`ensureLoaded()` /
  `invalidate()`). Call `invalidate()` after any create/update/delete in the
  Settings managers so the next `ensureLoaded()` picks up the change.

Theme bootstrap: `index.html` has an inline, non-module `<script>` *before*
the deferred `type="module"` entry point. `type="module"` scripts always run
after a plain inline script earlier in `<body>`, so this script applies the
`.dark` class and the PWA `theme-color` meta tag from
`localStorage`/`matchMedia('(prefers-color-scheme: dark)')` before
`useThemeStore`'s module-eval-time `initialDark` is computed — avoiding a
light-mode flash on devices with a dark OS theme. `store/index.js` also
registers a `matchMedia` `change` listener (guarded with `typeof
window.matchMedia === 'function'` for jsdom) so the app follows live OS theme
changes, but only while the user hasn't manually overridden the theme (no
`armarium-theme` key in `localStorage`).

### 5.2 API layer

All HTTP calls go through `src/api/client.js` (axios instance):
- relies on the browser sending the `access_token` httpOnly cookie
  automatically (same-origin) — no token handling in JS
- formats FastAPI's `{"detail": ...}` error payloads (including 422
  validation-error arrays) into readable `Error` messages
- on 401: clears the cached user profile, tells the service worker to drop
  cached `/api/` responses, and redirects to `/login`

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
- `BarcodeDisplay` (`src/components/ui/BarcodeDisplay.jsx`) renders a stored
  `item.barcode` as an actual barcode image (via `react-barcode`/`jsbarcode`,
  client-side SVG, no network calls), theme-aware via `useThemeStore`. Shown
  on films_tv/music item detail pages, under the Details card.
- `ListsMultiSelect` (`src/components/lists/ListsMultiSelect.jsx`) is a
  chip-toggle picker for an item's list memberships, scoped to its category
  via `useReferenceDataStore`'s `lists` — renders nothing if no lists exist
  yet for that category. Used by `MetadataForm` (add flow) and `ItemDetail`
  (edit mode).
- The Add Item flow (`AddFlow.jsx`) has a third option alongside
  Physical/Digital on its type step — "List" — which creates a new `ItemList`
  for the chosen category (`ListNameStep.jsx`), then lets the user search the
  library and add items to it (`ListItemsStep.jsx`), before landing on that
  category's Library view pre-filtered to the new list.

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

### 5.5 Mobile & PWA layout rules

Armarium is installed as a PWA on phones; mobile layout regressions are as
serious as desktop ones. **Every UI task must be visually verified at
≤ 390 px viewport width** (iPhone 15 / SE size) before being considered done.

Rules that prevent the most common regressions:

- **`SettingsLayout` tab bar: max 3 tabs.** Four or more tabs overflow on
  375 px screens. Route new settings sections as standalone pages (like
  `settings/plex` and `settings/lists`) and add them to `MANAGE_LINKS` in
  `lib/navigation.js`. Never add a fourth tab to `SettingsLayout`.
- **Tile grids (`TypeStep`, etc.): max 3 columns on mobile.**
  Use `grid-cols-2 sm:grid-cols-4` (or `grid-cols-4` with `text-xs sm:text-sm`
  and `py-3 sm:py-4`) so tiles stay readable at 375 px. Long labels wrap
  gracefully inside a tile; two-row labels are acceptable. Four columns
  total is the maximum even on desktop — prefer 3 if labels are long.
- **Dropdown panels:** use `min-w-full w-max max-w-[20rem]` on
  `SelectMenu` dropdowns and `min-w-full w-max max-w-[22rem]` on
  `LocationPicker` panels so they expand to fit content without overflowing.
  The trigger button always `truncate`s its label; use `title=` for the full
  value tooltip.
- **Filter panels (`FilterPanel`):** use `flex flex-wrap gap-3`. Each
  control has an explicit width class (`w-36`–`w-48`); controls stack
  automatically on mobile. Do not add `overflow-hidden` to the filter row.
- **`MobileTabBar`:** the bottom nav supports up to 6 tabs
  (`grid-cols-6`). Do not add more tabs without considering icon-only mode
  at 320 px.

### 5.6 PWA / offline

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

CI (`.github/workflows/ci.yml`) runs all of this on every push to `main` and
every PR. Run locally before committing structural changes:

**Backend** (from `backend/`, with `.venv` activated):
```bash
pip install -r requirements.txt -r requirements-dev.txt   # requirements-dev.txt: test/lint/SAST tools, not in the production image
python -m pytest -q          # full test suite (200 tests)
ruff check app                # lint
bandit -r app -ll              # SAST — see "accepted findings" below
pip-audit                       # dependency CVEs
```

A separate `backend-postgres` CI job runs `alembic upgrade head` against a
real `postgres:16-alpine` service container via
`scripts/verify_postgres_baseline.py` — SQLite is the default and primary
target (§1), but this catches Postgres-only DDL/seed-data regressions in
`alembic/versions/0001_baseline.py`.

**Frontend** (from `frontend/`):
```bash
npm run build                  # production build must succeed
npm test -- --run               # vitest
npm run lint                     # eslint
npm audit                        # dependency CVEs
```

### Accepted/suppressed findings

- **bandit B608** (`app/services/search.py`): the FTS5 trigger-creation SQL
  interpolates `FTS_COLUMNS`, a fixed module-level constant, not user input —
  a false positive. The trigger SQL is built into named variables before
  `text()`/`execute()`, and each of the 3 flagged assignment lines carries a
  precise `# nosec B608`; don't blanket-disable or restructure this code
  further to satisfy bandit.
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

If the new model has a many-to-many relationship with another model, follow
the `ItemList`/`media_item_lists` pattern described in §4.2 (association
`Table`, one-directional `relationship(secondary=...)`, and a repository
method that validates and replaces the collection wholesale).

## 10. Known tradeoffs & areas for deeper review

These are intentional-for-now decisions or known gaps, not bugs — listed so
future work can revisit them deliberately rather than rediscover them:

- **Large page/component files** (`Admin.jsx`, `ItemDetail.jsx`,
  `BarcodeScanner.jsx`, `AddFlow.jsx`) mix multiple concerns (several
  settings panels, multiple modals/steps). Splitting these into smaller
  components would improve readability but touches a lot of working code —
  do incrementally, one panel/step at a time, with manual UI verification.
- **Frontend test coverage is improving but still partial** —
  `lib/reorder.js`, `hooks/useStepHistory.js`, `pages/Library.jsx`,
  `pages/Admin.jsx`, and several `components/add/*` steps have tests.
  `ItemDetail.jsx` and `BarcodeScanner.jsx` do not yet — adding tests for
  these (and any other page/component you touch) is encouraged.

## 11. Documentation map

Keep these in sync when a change touches them — most changes only need one
or two:

| Document | Covers | Update when... |
|---|---|---|
| [README.md](README.md) | User-facing features, Quick Start, configuration reference, supported media types, usage | A user-visible feature, config variable, or setup step changes |
| [ARCHITECTURE.md](ARCHITECTURE.md) (this file) | Backend/frontend conventions, layering, repository pattern, quality gates | A convention is added, removed, or contradicted by your change |
| [CLAUDE.md](CLAUDE.md) | Entry point for Claude Code / AI assistants — points here and to the quality-gate commands | The quality-gate commands or top-level conventions change |
| [CONTRIBUTING.md](CONTRIBUTING.md) | PR process, issue templates, code style | The contribution workflow or required local checks change |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Fresh local dev environment setup (VS Code, Mac/Linux), running tests | Dev environment setup, tooling, or test commands change |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deploying tagged releases via prebuilt Docker images | The release process, `docker-compose.prod.yml`, or supported deployment targets change |
| [CHANGELOG.md](CHANGELOG.md) | Per-version release notes (Keep a Changelog format) | Any user-facing change — add an entry under `[Unreleased]` |
| [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) | Dependency licences and third-party attribution | A dependency (backend `requirements*.txt` or frontend `package.json`) is added, removed, or its licence changes |
| `.env.example` | Template for runtime configuration | A new environment variable is added to `app/config.py` |
