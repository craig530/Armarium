# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.10.0] - 2026-06-24

### Added

- **Cover photo upload when adding an item** — the Add Item form now has the
  same "upload a photo" option as editing, instead of only a cover image
  URL field.
- **Duplicate warning when adding an item** — saving now checks for an
  existing item with the same title and medium and asks you to confirm
  before adding a second copy. Cancelling resets the form (or, in batch
  mode, skips straight to the next scan).

### Changed

- **Linked copies without their own cover now borrow one** — if a physical
  copy and its linked digital copy aren't both covered, the one missing a
  cover now shows the other's instead of a blank cover.

### Fixed

- **Batch scanning lost the scanner off-screen after each save** — saving
  an item in batch mode now scrolls back to the top so the scanner is
  visible for the next scan.

## [1.9.0] - 2026-06-23

### Added

- **Default platforms and locations** — a fresh database (or a database
  reset) now seeds 8 starter platforms (Plex, Audible, Kindle, PlayStation
  Store, Microsoft Store, Nintendo eShop, Apple TV, Amazon Music) and 3
  starter locations (Living Room, Master Bedroom, Office), the same way
  default media subtypes already were. Only applies when the
  platforms/locations table is empty — an admin's own existing platforms or
  locations are never touched.
- **Themed empty-collection icons** — each category's "no items yet" state
  now shows an icon matching its medium (a stack of discs for Music, a
  clapperboard for Films & TV, a bookshelf for Books, a gamepad for Games,
  a stack of boxes for "All") instead of a single generic box.

### Changed

- **Default Games mediums simplified** — the six console-specific defaults
  (Nintendo Switch, Xbox, PlayStation; Nintendo eShop, Microsoft Store,
  PlayStation Store) are replaced by three format-based ones: Disc and
  Cartridge (Physical), Game (Digital). Existing games using an old default
  keep their current medium — nothing is deleted out from under real data.

### Fixed

- **Mobile filter panel didn't fill the screen width** — expanded filters
  on mobile now lay out in a 2-column grid that fills the full width
  (50/50), with an odd trailing filter left-aligned on its own row,
  instead of an uneven flex-wrap of fixed-width fields.
- **Admin page had no way back to Settings on mobile/PWA** — added a
  "← Settings" link at the top, matching the existing "← Admin" link on
  the Users page.

## [1.8.3] - 2026-06-23

### Added

- **Email-based user invites and password resets** — adding a user now
  asks for an email instead of a password; the new account gets a link to
  set its own password. Admins can force a password reset on any existing
  user (immediately invalidating their current password) from the same
  email-link flow. The login screen gained a "Forgot password?" option for
  self-service resets. None of this applies to the admin account defined
  by `ADMIN_USERNAME`/`ADMIN_PASSWORD` in `.env`, which is managed there
  and via restart, not through the UI. Requires SMTP to be configured
  (`SMTP_HOST` etc. in `.env`) — see README's Configuration section.

## [1.8.2] - 2026-06-22

### Fixed

- **Setting up Plex sync again after removing it failed** — `PlexConfig`'s
  singleton row relied on the `id` column's autoincrement default to land
  on 1 (enforced by a check constraint), but on PostgreSQL the underlying
  sequence keeps advancing even after the row is deleted, so reconfiguring
  Plex after a previous removal permanently hit the check constraint and
  500'd on save (test connection still succeeded, since it doesn't touch
  the database). The row's `id` is now always set explicitly to 1.

## [1.8.1] - 2026-06-22

### Fixed

- **Reset database failed when Plex integration was configured** — the
  admin "Reset database" action deleted media subtypes and platforms
  without first clearing the Plex sync config and library mappings that
  reference them, hitting a foreign key violation (always enforced on
  PostgreSQL, surfacing as a 500). Reset now clears the Plex integration
  and its library mappings before wiping the catalogue.

## [1.8.0] - 2026-06-22

### Added

- **Dedicated Users page** — user management moved from the Admin page to
  its own screen (`/admin/users`), so households with many accounts aren't
  stuck scrolling a long inline list buried among other admin cards. The
  Admin page now shows a compact "N users" summary card linking there.
- **System Info: configured port** — alongside the externally-observed
  port (e.g. 443 through a reverse proxy), the Admin System Info panel now
  also shows the `PORT` value configured in `.env`/docker-compose, wired
  through as an actual setting rather than inferred from the browser alone.
- **Export progress feedback** — the library CSV/JSON export buttons
  (Settings and the navbar menu) now disable and show a spinner while the
  export is in flight, instead of giving no indication that anything is
  happening for large libraries.
- **Schedule last-run time** — maintenance/Plex sync schedule rows in the
  Admin panel now show "last ran Xh ago" (highlighted red with the error
  message on failure) alongside the next scheduled run.

### Changed

- **Theme toggle icon** reflects the current state instead of what
  clicking it would switch to: a combined sun/moon glyph for Auto,
  otherwise whichever of Light/Dark is actually active.
- **Search placeholder is category-aware** — "artists" for Music,
  "directors" for Films & TV, "authors" for Books, "developers" for Games,
  instead of one generic placeholder mentioning roles that don't apply to
  the category you're searching.
- **Footer**: "Armarium" now links to armarium.app.
- Removed em-dashes from user-facing text app-wide (toasts, labels,
  placeholders, confirmation dialogs) in favour of plain punctuation.

### Fixed

- **Admin Users mobile layout** — rows now stack vertically on narrow
  screens instead of cramming the user info and action icons into one row;
  badges wrap instead of overflowing; the password/display-name edit input
  no longer overlaps the save/cancel buttons.

## [1.7.1] - 2026-06-22

### Added

- **Multi-arch GHCR images** — `armarium-backend`/`armarium-frontend` are
  now built for both `linux/amd64` and `linux/arm64`, so the prebuilt-image
  deployment flow (`docker-compose.prod.yml`) works on ARM hosts (Raspberry
  Pi, AWS Graviton, Oracle Cloud's ARM free tier, Apple Silicon Macs)
  without needing `--platform` overrides or building from source.

### Fixed

- **GHCR packages were private despite the repo being public** — container
  package visibility doesn't automatically follow repository visibility
  (it's set once, independently, and this repo was originally private).
  Anonymous `docker pull` of either image returned "unauthorized" until
  visibility was changed manually for both packages.
- **Flaky Plex sync tests** — a process-global job-status dict wasn't
  cleared between tests, so a sync left at status="running" by one test
  (its background task not yet finished when that test's event loop was
  torn down) could be mistaken for an in-progress sync by a later, unrelated
  test reusing the same mapping id, causing intermittent CI failures.

### Security

- Upgraded `pydantic-settings` 2.14.1 → 2.14.2 (GHSA-4xgf-cpjx-pc3j) and
  pinned `msgpack` to 1.2.1 (GHSA-6v7p-g79w-8964, a dev-only transitive
  dependency of `pip-audit` — never shipped in the production image).

## [1.7.0] - 2026-06-19

### Added

- **Display names** — users can set a display name (Settings → Profile),
  shown in the navbar and on owned items, falling back to `@username` when
  unset.
- **Theme preference** — Light/Dark/Auto, chosen from a 3-button grid in
  Settings → Profile, persisted to your account and synced across devices on
  login (previously theme was a local-only browser preference).
- **Admin Ownership panel** — switch between "Shared" and "By User" ownership
  modes from the Admin panel, including a one-time migration tool to assign
  existing shared items, lists, and Plex mappings to a chosen user before
  switching.
- **Owner visibility on items** — item detail pages show an owner row
  (clickable to filter the library by that owner); linked copies owned by a
  different user show that owner's name alongside them.
- **UPCDatabase.org barcode fallback** — when resolving a scanned Films & TV
  or Games barcode to a product title, if UPCitemdb has no match for the
  code, Armarium now optionally falls back to UPCDatabase.org. Enabled by
  setting `UPCDATABASE_API_KEY` in `.env`; with no key set, behaviour is
  unchanged.
- **GTIN-14 / ITF-14 barcode support** — some Nintendo Switch cartridge boxes
  use a 14-digit barcode (a packaging-indicator digit plus an EAN-13); these
  are now recognised by stripping the leading digit and retrying as EAN-13.
- **System Info panel** — the Admin page now shows the running build
  version, online status, database backend, the port you're connected on,
  and which metadata APIs (TMDB, IGDB, UPCDatabase.org) have credentials
  configured.

### Changed

- **Medium Visibility** (renamed from "Category Visibility") — the Admin
  panel toggle for disabling entire categories now shows the current item
  count per category.
- **Navbar cleanup** — removed the "Manage" dropdown in favour of direct
  links; shows your display name (with `@username` fallback) instead of just
  the username.
- **Trademark disclaimer** — the README, in-app footer, and
  THIRD_PARTY_LICENSES.md now explicitly state that Armarium is an
  independent open-source project not affiliated with, endorsed by,
  sponsored by, or otherwise associated with any retail, console or
  publisher brand (in addition to the metadata/lookup providers already
  named), since the app catalogues and displays third-party product/brand
  names and logos for games, films, music and books.

### Fixed

- **Scheduled jobs could be delayed, or never run at all, across restarts** —
  APScheduler re-registers every job fresh on each backend restart. A job
  that had run before anchored its next fire to `last_run_at + interval`,
  but a job that had *never* run anchored to "registration time + interval"
  instead — and since registration happens on every restart, a host that
  redeploys more often than the job's interval could reset that countdown
  indefinitely, so the job never got a chance to fire (this happened in
  production: four schedules created days earlier had never executed once).
  Now consistently anchors to `last_run_at`, or `created_at` if the job has
  never run, so an overdue first run fires on the next scheduler tick
  instead of waiting indefinitely.
- **Location/platform chip tooltips clipped by container overflow** — the
  hierarchical-path tooltip on location chips is now rendered via a portal
  so it's never clipped by an `overflow-hidden` ancestor.
- **Location chip tooltip misbehaving on mobile/PWA** — touch browsers
  emulate a synthetic `mouseenter`→`click` sequence after every tap, which
  could show a duplicate tooltip alongside the long-press one, leave a
  tooltip stuck open (no real `mouseleave` follows on a touch device), or
  flash briefly on a plain tap meant to filter the library. The hover
  tooltip now only activates on devices with real pointer-hover support;
  mobile continues to use the long-press tooltip exclusively.
- **Disabled-category flash on load** — `appConfig` is now persisted to
  `localStorage`, so the navbar and home page no longer briefly show a
  disabled category before the first API response arrives.
- **Games metadata silently broken on `docker-compose.prod.yml` deployments**
  — that compose file never passed `IGDB_CLIENT_ID`/`IGDB_CLIENT_SECRET`
  through to the backend container's environment, even when set correctly in
  `.env`. Anyone deploying via the documented prebuilt-image flow (rather
  than building from source with `docker-compose.yml`, which already had
  this) got no Games search/barcode lookup, with no indication why. Also
  added the new `UPCDATABASE_API_KEY` passthrough to both compose files.
- **Item cover image not refreshing after upload/delete** — the item detail
  hero image now remounts on every cover change instead of potentially
  showing a cached/stale image.
- **Duplicate "More by this artist/author" entries** — deduplicated.

### Security

- Upgraded `undici` (transitive, via `jsdom`) to patch a high-severity CVE
  flagged by `npm audit` — TLS certificate validation bypass and cross-user
  cache information disclosure (GHSA-vmh5-mc38-953g, GHSA-pr7r-676h-xcf6).

## [1.6.1] - 2026-06-18

### Fixed

- **Fresh-install admin account never created** — `UserRepository.any_exist()`
  previously counted all users including the hidden shared system user inserted
  by migration 0007. On a clean install, `_ensure_admin()` saw a user already
  existing and silently skipped creating the admin account, leaving the instance
  with no way to log in. Fixed by filtering `is_system = False` in `any_exist()`.

## [1.6.0] - 2026-06-18

### Added

- **Category visibility** — admins can disable top-level media categories
  (Music, Films & TV, Books, Games) from the Admin panel. Disabled categories
  are hidden from all navigation (desktop sidebar, mobile tab bar), the home
  page browse rows, the add flow type picker, and the category filter dropdown.
  Navigating directly to a disabled library URL redirects to the home page.
  Allows running Armarium as a focused single-category catalog (e.g. games
  only) without the other sections appearing anywhere in the UI.
- **`disabled_categories` field on `GET /api/v1/admin/config`** — now
  accessible to all authenticated users (not admin-only) so the frontend can
  apply visibility rules without an extra admin check. Updating disabled
  categories is still admin-only via `PUT /api/v1/admin/config`.

### Changed

- `GET /api/v1/admin/config` is now accessible to all authenticated users
  (previously admin-only). The response includes `disabled_categories` needed
  by the UI.

## [1.5.0] - 2026-06-18

### Added

- **Ownership** — every media item, list, and Plex library mapping now has an
  owner linked to a user account. The default ownership mode is "Shared"
  (items belong to a hidden system user), with "By Login" mode available for
  multi-user setups where each item is owned by the person who created it.
- **Owner field on item detail** — items show an owner chip in view mode;
  tapping it navigates to the library filtered by that owner. In edit mode a
  dropdown lets admins reassign ownership to any user.
- **Owner filter in Library** — a new Owner filter in the filter panel lets
  users browse items by owner.
- **Owner per Plex library mapping** — each Plex library sync can target a
  different user; new items created by that sync are owned by the configured
  user.
- **Library Ownership settings page** — new standalone Settings → Ownership
  page with radio buttons for Shared / By Login modes. Switching to By Login
  mode requires a one-step migration that reassigns all existing items, lists,
  and Plex mappings to a chosen user.
- **Owner displayed on lists** — in filter dropdowns, lists owned by a
  non-shared user are shown as "Name (username)" so users can distinguish
  same-named lists created by different people.
- **`GET /users/summary`** — new endpoint available to all authenticated users
  (not admin-only) returning `[{id, username}]`, used to populate owner
  pickers without exposing admin user data.
- **`plex_rating_key` in media response** — the field was stored but
  accidentally omitted from the API response payload; now always returned.

### Changed

- Admin `GET /users` and `GET /users/summary` now exclude the internal
  `shared` system user from all results.
- Migration `0007`: adds `is_system` to `users`, inserts the shared system
  user, creates `app_config` singleton table, adds `owner_id` to
  `media_items` / `item_lists` / `plex_library_mappings`, and updates the
  `item_lists` unique constraint from `(category, name)` to
  `(category, owner_id, name)`.

## [1.4.2] - 2026-06-18

### Added

- **"Open in Plex" button** — item detail screens for music, films, and TV items
  that belong to the configured Plex platform now show an "Open in Plex" link.
  The button is enabled when the item has a Plex rating key (set automatically
  on the next sync after upgrading) and disabled (with tooltip) when the item
  was created manually or hasn't yet been synced. The button is hidden entirely
  when Plex sync is not configured. The Plex server's machine identifier is
  fetched and stored when saving the Plex configuration so deep-link URLs can
  be constructed client-side.
- **Location chip navigation** — single-tapping a location chip in library card
  and list views now navigates to the filtered library for that location (same
  behaviour as list chips added in v1.4.1).
- **Platform chip navigation** — single-tapping a platform chip navigates to the
  filtered library view for that platform.

### Fixed

- **Location long-press (all library views)** — the 10 px movement threshold
  added to the touchmove cancel handler means natural finger tremor no longer
  cancels the long-press before the 500 ms timer fires. Applies to all
  library views (All, Music, Films & TV, Books, Games).
- **Tooltip clipped on all browsers** — removed `overflow-hidden` from the
  OwnershipRow container, which was clipping the absolutely-positioned tooltip
  panel on every browser, not just Safari.
- **Tooltip on Safari desktop** — replaced the CSS `group-hover` approach
  (unreliable on non-interactive spans in Safari) with JS `onMouseEnter` /
  `onMouseLeave` state, making the full-path tooltip work in all browsers.
- **Game barcode lookup** — added an EAN-13 fallback: if a 12-digit UPC-A
  barcode yields no result from UPCitemdb, the lookup is retried with the
  EAN-13 equivalent (prepend "0"). North American game barcodes are UPC-A but
  UPCitemdb indexes them as EAN-13.

### Changed

- Migration `0006`: adds `plex_rating_key` (String 50, indexed) to
  `media_items` and `machine_identifier` (String 100) to `plex_config`.

## [1.4.1] - 2026-06-16

### Added

- **Lists clickable in library cards** — tapping a list chip shown below an item
  in grid and list views now navigates to the filtered library view for that list.
- **Lists section on item detail** — the item detail screen (view mode) now shows
  a "Lists" section listing every list the item belongs to; each list is a button
  that navigates to the filtered library view.
- **ISBN barcode on book detail** — books now display a barcode image rendered
  from their ISBN on the detail screen, matching the existing behaviour for
  music, films & TV, and games.

### Fixed

- **Location long-press on mobile** — long-pressing a location chip in library
  card/list views now reliably shows the full path popover without navigating to
  the item detail screen; a synthetic click following the touch-end event is
  suppressed when the long-press triggered.
- **Custom location tooltip on desktop** — the browser-default `title=` tooltip
  on location chips and the overflow `+N` chip has been replaced with a styled
  dark tooltip that matches the app theme.
- **Star rating on its own line** — on item detail screens for books and music
  (where the creator is rendered as a link), the star rating now appears on a
  separate line below the creator name instead of flowing inline next to it.
- **Music cover art square** — album cover art now displays as square (1:1
  aspect ratio) everywhere it appears: item detail hero (view and edit modes),
  MetadataForm confirm/edit preview, and the recently-added / batch-session list
  in the add flow.

### Changed

- **Backend logging** — added structured logging to the Plex sync router
  (INFO on sync start and completion with item counts; ERROR with stack trace on
  failure) and the auth router (WARNING on failed login attempts with username
  and client IP). Logging conventions documented in ARCHITECTURE.md §4.9.

## [1.4.0] - 2026-06-16

### Added

- **Plex sync scheduling** — each Plex library mapping can now have a recurring
  sync schedule (every 1 h / 6 h / 12 h / 24 h / weekly), set and managed from
  the Plex settings page. Scheduled syncs persist across restarts (stored in the
  new `scheduled_jobs` table) and are driven by APScheduler running within the
  backend process.
- **Sync status detail** — the Plex sync result now shows last-run time, status
  (completed / cancelled / error), and separate counts for items created,
  updated (metadata changed), and removed. The "updated" count only increments
  when metadata actually changed, so repeated scans of an unchanged library
  read as 0 updates rather than "all items updated".
- **Manual sync: choose whether to auto-remove stale items** — a per-mapping
  "Auto-remove missing items" checkbox on the Plex settings page (default: off)
  controls whether a manual sync deletes items no longer in Plex. Previously
  this could only be triggered separately.
- **Scheduled sync: auto-remove in setup** — when configuring a scheduled Plex
  sync, you can opt in to auto-remove items no longer in Plex on each scheduled
  run (default: on for scheduled syncs).
- **Efficient delta sync** — on re-syncing an item that already exists, covers
  are not re-downloaded (the largest cost). Only metadata fields that actually
  differ are written.
- **Library Maintenance panel** — the Admin panel now consolidates four
  maintenance tasks (scan & link duplicate copies, redownload all covers, purge
  orphan covers, export covers), each with a "Run now" button and its own
  recurring schedule (replacing the separate Cover Images panel).
- **Scheduled backups** (SQLite only) — the Database Backups panel now includes
  a recurring schedule option alongside the existing "Backup now" button.
- **Export covers schedule** — the export-covers scheduled task accepts a base
  directory on the server; the export is saved to a date-stamped subfolder.
  Scheduled exports are limited to once per calendar day.
- **`can_manage_schedules` permission** — new per-user flag (default: on).
  Non-admin users with this flag can create, edit, and remove Plex sync
  schedules. Without it they see schedule info (read-only) but cannot modify
  schedules. Manual sync is unaffected by this flag. Admin maintenance
  schedules remain admin-only regardless.

## [1.3.0] - 2026-06-16

### Added

- **Item counts on library views** — Music, Films & TV, Books, and Games pages
  now display the total item count next to the category heading. When filters
  are active the count shows as "X of Y items" so you can see what the filter
  found versus the full catalogue.
- **Rating filter** — all library and home views now include a "Rating" filter
  with options: Any rating / No rating / 3 stars or more / 4 stars or more /
  5 stars.
- **Rating overlay on covers** — items with a user rating show a subtle
  vertical star strip on the left edge of the cover image, starting below the
  subtype badge, so ratings are visible without opening the item.
- **Carousel navigation buttons** — the home-page category carousels now show
  left/right scroll buttons, and the scroll container supports click-drag (mouse)
  or touch-swipe.
- **Location chip shows leaf name + full-path tooltip** — on item cards and
  list rows, the location tag now shows only the leaf node name to save space.
  On desktop, hovering shows the full hierarchy path as a tooltip; on mobile/PWA
  a long-press (500 ms) reveals a popover with the full path that auto-dismisses.
- **Add item — dynamic step counter** — the step counter on the "Add item"
  wizard is now hidden until the user selects Physical, Digital, or List,
  so the first screen is cleaner and avoids the misleading "Step 1 of 4"
  before a mode is chosen.
- **Delete location/platform with reassignment** — when deleting a location or
  platform that still has items linked to it, a modal now offers to move all
  those items to another location/platform first (or unassign for locations),
  then deletes. Previously this resulted in a blocking error.
- **Game icon background** — game platform icons (Nintendo Switch, Xbox,
  PlayStation) on item cards now have the same coloured badge background as
  all other subtype icons, matching Physical and Digital entries.

## [1.2.2] - 2026-06-16

### Added

- **Smart filter options** — the location and platform filter selectors now only
  show options that have at least one item in the current view (category,
  supertype, list, and search query all applied). Empty locations and platforms
  are hidden so every choice produces results. Powered by a new
  `GET /api/v1/media/facets` endpoint.

### Fixed

- **"Add item" category row overflow** — Music, Films & TV, Books, and Games
  now fit on a single row across all screen sizes (changed to a 4-column grid
  with slightly smaller text/icons on mobile), keeping the supertype row
  (Physical / Digital / List) on the row below.
- **Settings > Lists on mobile** — the Lists section has been moved from the
  settings tab bar to its own standalone page (like Plex), preventing the tab
  bar from overflowing on narrow mobile viewports (≤ 375 px). It remains
  accessible from the settings sidebar nav.
- **Filter dropdown clipping** — the location and platform filter dropdowns now
  expand to fit their content (up to a max width) rather than being clamped to
  the button width, preventing long location names and deep hierarchy paths
  from being clipped. The location button trigger also shows only the leaf
  name, with the full path available as a tooltip.

## [1.2.0] - 2026-06-16

### Added

- **Games category** — a new top-level media category for video games, alongside
  Music, Films & TV, and Books. Games appear in the "All" home view and have
  their own nav link (desktop sidebar and mobile tab bar).
- **Default game media types** — fresh installs (and reset installs) are seeded
  with six game subtypes: Nintendo Switch, Xbox, and PlayStation (physical);
  Nintendo eShop, Microsoft Store, and PlayStation Store (digital).
- **IGDB metadata lookup** — search and barcode lookup for games powered by
  [IGDB](https://www.igdb.com/) (Internet Game Database). Requires
  `IGDB_CLIENT_ID` + `IGDB_CLIENT_SECRET` in `.env` (Twitch developer
  credentials). IGDB attribution logo shown on game item pages and in the
  game search picker.
- **Developer field** — game items have a dedicated "Developer" field (the
  studio/publisher) that shows on the item detail page.
- **Barcode display for Games** — scanning a retail game barcode now shows it
  as a visual barcode image on the item detail page, consistent with Films &
  TV and Music.
- **Game platform logos** — built-in platform logos for Steam, PlayStation,
  Xbox, Nintendo eShop, Microsoft Store, Epic Games Store, GOG.com, and
  itch.io, extracted from [simple-icons](https://simpleicons.org/) or
  hand-crafted SVGs where a simple-icons entry doesn't exist.
- **`IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` config** — new optional settings
  in `.env.example`; game metadata lookup is gracefully disabled (503) when
  not set.

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

### Security

- Upgraded `python-multipart` from 0.0.27 to 0.0.31 to resolve
  CVE-2026-53538, CVE-2026-53539, and CVE-2026-53540.

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

[Unreleased]: https://github.com/craig530/Armarium/compare/v1.6.1...HEAD
[1.6.1]: https://github.com/craig530/Armarium/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/craig530/Armarium/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/craig530/Armarium/compare/v1.4.2...v1.5.0
[1.4.2]: https://github.com/craig530/Armarium/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/craig530/Armarium/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/craig530/Armarium/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/craig530/Armarium/compare/v1.2.2...v1.3.0
[1.2.2]: https://github.com/craig530/Armarium/compare/v1.2.0...v1.2.2
[1.2.0]: https://github.com/craig530/Armarium/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/craig530/Armarium/releases/tag/v1.1.2
[1.1.1]: https://github.com/craig530/Armarium/releases/tag/v1.1.1
[1.1.0]: https://github.com/craig530/Armarium/releases/tag/v1.1.0
[1.0.1]: https://github.com/craig530/Armarium/releases/tag/v1.0.1
[1.0.0]: https://github.com/craig530/Armarium/releases/tag/v1.0.0
