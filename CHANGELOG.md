# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.2] - 2026-06-16

### Added

- **More by same author/artist** — the item detail page for books and music now
  shows a horizontal strip of other items in your library by the same author or
  artist (excluding the item itself and any linked copies already shown in the
  Ownership section).
- **Author/artist as search link** — clicking the author name on a book detail
  page or the artist name on a music detail page navigates to the library view
  pre-filtered to that creator's name.
- **Batch mode default list** — when one or more lists exist for the current
  category, the Batch Mode step now offers an optional "Default list" picker so
  every item saved in the session is automatically added to that list.
- **Cover art in list item picker** — the "Add items to list" step in the Add
  Item flow now shows a small cover thumbnail alongside each item row.
- **List chips on item cards** — the library card and list-row views now show
  which custom list(s) an item belongs to alongside its location/platform chips.
- **Correct step count for the List branch** — the Add Item wizard now shows
  three progress dots (Type → Name → Items) instead of four when creating a
  new list, matching the actual number of steps in that branch.

### Fixed

- Long location paths, platform names, or deep location hierarchies no longer
  overflow their chip container on item cards and list rows; chips are now
  capped at a maximum width and truncate cleanly.

## [1.1.1] - 2026-06-15

### Fixed

- Migration `0003_add_media_lists` failed with `type "mediacategory" already
  exists` when upgrading an existing deployment from v1.0.x/v1.1.0 on
  PostgreSQL, leaving the backend crash-looping. The `item_lists.category`
  column declared its enum as `sa.Enum(..., create_type=False)`, but the
  generic `sa.Enum`'s `create_type` flag is silently dropped when SQLAlchemy
  adapts it to PostgreSQL's native `ENUM` type, so Alembic still attempted
  (and failed) to recreate the already-existing `mediacategory` type. Fixed
  by using `postgresql.ENUM(..., create_type=False)` directly, which
  correctly suppresses the `CREATE TYPE`.

## [1.1.0] - 2026-06-15

### Added

- **Lists** — create named, category-scoped lists (e.g. "Want to read" under
  Books, "Favourites" under Music) and organise your items into them:
  - A new "List" option alongside Physical/Digital in the Add Item flow lets
    you name a new list and immediately search your library to add items to
    it.
  - Manage lists (rename, delete, view item counts) from a new Settings →
    Lists section, alongside Locations and Platforms.
  - Edit an item's list memberships directly from its create/edit forms via a
    chip-style multi-select.
  - Filter the All, Music, Films & TV and Books screens by list.
  - A new `can_manage_lists` permission (on by default) controls who can
    create, rename or delete lists; everyone can still filter by and assign
    them.
- A personal 5-star rating, settable on any item from its detail page —
  click a star to rate, click the current rating again to clear it.
- Films & TV item details now show TMDB's user rating ("TMDB Rating") when
  available.
- Films & TV and music items with a scanned barcode now show it as an actual
  barcode image on their detail page, alongside the existing text value.

### Changed

- Filtering the Library by a location now also includes items stored in that
  location's sub-locations (e.g. filtering by "Office" also matches items in
  "Office → Shelf").
- Single-item lookups (barcode/ISBN scan) now fall back to additional cover
  art sources when the primary provider has none: MusicBrainz barcode
  lookups fall back from a release's cover to its release-group's cover, and
  ISBN lookups fall back to Google Books when Open Library has no cover.
  Films & TV lookups fall back from a missing poster to the backdrop image.
- Auto-linking items of the same title now also matches by title and release
  year when no exact TMDB/MusicBrainz/ISBN id match is found (e.g. linking a
  newly-scanned CD to a Plex-synced digital copy that has no MusicBrainz id),
  guarded against linking items with an explicitly different `edition`.
- The "Manage Media Types" permission toggle in user settings is now labelled
  "Manage Mediums", matching the 1.0.1 "Mediums" rename.

### Fixed

- Light/dark mode now correctly follows the device's `prefers-color-scheme`
  on first load in mobile browsers and the installed PWA, and live-updates if
  the OS theme changes while the app is open (unless you've manually toggled
  the theme).
- Scanning a Films & TV barcode (e.g. a Blu-ray/DVD) now returns results —
  previously always returned nothing, since TMDB has no barcode lookup of
  its own and no fallback was wired up.

## [1.0.1] - 2026-06-15

### Changed

- Renamed the "Manage Locations" / "Manage Platforms" / "Manage Media Types"
  settings sections to "Locations" / "Platforms" / "Mediums" — they're
  already grouped under a "Manage" menu/heading, so the longer names were
  redundant and cramped on mobile. The "New media type" button is now "New
  medium".
- Confirmation dialogs now show button text that matches the action (e.g.
  "Unlink", "Remove", "Redownload", "Scan & Link", "Stop syncing") instead of
  a generic "Delete" for every confirmation.

### Added

- Resetting the database from the Admin Danger Zone now requires a second
  confirmation step where you must type `RESET` to proceed, on top of the
  existing warning dialog.

### Fixed

- Self-host the Inter and Fraunces fonts (via `@fontsource`) instead of
  loading them from Google Fonts. The previous `<link>` tags were silently
  blocked by the app's Content-Security-Policy (`style-src 'self'`), so the
  UI always fell back to system fonts. This also removes an external
  dependency/privacy leak on a self-hosted app.
- The Admin "Database Backups" panel is now disabled with an explanation
  when running on PostgreSQL, where built-in backups aren't supported,
  instead of silently failing when "Backup now" is clicked.
- The Plex Sync settings page no longer overflows on mobile/PWA — each
  library's sync status, sync button and remove button now wrap onto their
  own row instead of pushing the remove button off-screen.
- Book covers from Open Library's `covers.openlibrary.org` host failed to
  download or display when archive.org served them via a second redirect
  (`.../download/<collection>.zip/<file>` → `.../view_archive.php?...`,
  used for covers stored inside a zipped collection). The cover fetcher only
  followed a single redirect hop; it now follows up to three.

## [1.0.0] - 2026-06-14

Initial public release.

### Cataloguing

- Catalogue physical and digital media across three categories: Music, Films
  & TV, and Books.
- Customisable media types ("subtypes") within each category — CD, DVD,
  Blu-ray, 4K Blu-ray, Digital Film, Digital TV Series, Streaming Music,
  Streaming Film, Streaming TV, Book, Graphic Novel and more, with the
  ability to add, rename and reorder your own.
- Barcode scanning via the device camera for quick lookups.
- Manual entry and metadata search as alternatives to scanning.

### Metadata & Search

- Automatic metadata and cover art lookup from TMDB (Films & TV), MusicBrainz
  (Music) and Open Library (Books).
- Full-text search across the catalogue, with a fallback for environments
  without FTS5 support.
- Filtering and sorting by category, type, location, platform, genre and
  year.

### Organisation

- Hierarchical physical locations (e.g. room → shelf → box) with built-in and
  custom icons.
- Digital platforms (e.g. streaming services, storefronts) with built-in and
  custom logos.
- A Settings area for managing locations, platforms and media subtypes.

### Linking physical & digital copies

- Pair a physical and digital copy of the same title into a single unified
  entry with a combined ownership badge.
- Automatic matching of new items against existing ones using shared
  metadata identifiers.
- Manual linking and unlinking of items.

### Users & Security

- JWT-based authentication with a multi-user model and an admin role,
  including granular per-user permission flags (add items, manage locations,
  platforms, media types).
- Admin panel for creating and managing user accounts.
- httpOnly, `SameSite` session cookies for the web app, with
  `Authorization: Bearer` tokens for API/script access.
- SSRF protections on external URL fetches (cover art, Plex) and validated
  file uploads for covers, icons and logos.
- In-process rate limiting on sensitive endpoints.

### Import, Export & Backup

- CSV and JSON export of the full library, available to all users.
- Admin-only CSV and JSON import, with validation against existing data.
- On-demand and automatic backups, with old backups pruned automatically.

### Progressive Web App & UX

- Installable as a Progressive Web App, with offline browsing of your
  library.
- Dark mode.
- Keyboard shortcuts for common actions.

### Infrastructure

- Docker Compose deployment for production, plus a hot-reload development
  setup.
- Non-root, multi-stage Docker images for both backend and frontend.
- SQLite by default, with optional PostgreSQL support.
- Schema managed via Alembic migrations, with a repository-layer data-access
  pattern (`app/repositories/`) shared by all routers.
- CI pipeline (GitHub Actions) running linting, SAST (bandit), dependency
  audits, and the full test suite on every push and pull request.
- Versioned Docker images published to GHCR for each tagged release — see
  [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

[Unreleased]: https://github.com/craig530/Armarium/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/craig530/Armarium/releases/tag/v1.1.1
[1.1.0]: https://github.com/craig530/Armarium/releases/tag/v1.1.0
[1.0.1]: https://github.com/craig530/Armarium/releases/tag/v1.0.1
[1.0.0]: https://github.com/craig530/Armarium/releases/tag/v1.0.0
