# Working in this repo

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full architecture and
conventions — read it before making structural changes (new models, routers,
repositories, stores, or any change to auth/migrations/SSRF handling). Keep
it up to date: if a change adds, removes, or contradicts a convention
described there, update the doc in the same change. ARCHITECTURE.md §11 is a
map of which other doc (README, CHANGELOG, docs/DEVELOPMENT.md,
docs/DEPLOYMENT.md, THIRD_PARTY_LICENSES.md, `.env.example`) to update for a
given kind of change — check it before finishing a task.

New to this repo? [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) covers local
setup (including this file's role) in more depth.

## Quick reference

- **Backend layering is strict**: routers call repositories
  (`app/repositories/*.py`), repositories own all SQL, schemas
  (`app/schemas/*.py`) define the API contract. Don't write `select`/
  `delete` statements in routers — add a repository method.
- **Schema changes go through Alembic only** (`alembic revision
  --autogenerate`, then hand-check the generated migration). There is no
  other migration mechanism.
- **External URLs/files are untrusted** — new "fetch a URL" or
  "accept an upload" features must go through (or justify bypassing)
  `services/cover_art._is_safe_url` / `services/asset_upload.py`.
- **Frontend**: `lib/mediaIcons.js`, `lib/categories.js`, `lib/navigation.js`
  are the sources of truth for icon/category/nav data — don't redefine them
  locally in components. API calls go through `src/api/*.js` wrappers over
  `src/api/client.js`, never raw axios.
- **ESLint** (`eslint-plugin-react-hooks`) intentionally only enables
  `rules-of-hooks` + `exhaustive-deps`, not the v6+ "recommended" React
  Compiler-readiness rules — see ARCHITECTURE.md §7 before changing this.
- **Mobile/PWA layout** — verify every UI change at ≤ 390 px. Hard rules:
  `SettingsLayout` max **3 tabs** (add new sections as standalone pages);
  tile grids max **4 columns** with `text-xs sm:text-sm` on mobile; dropdowns
  use `min-w-full w-max max-w-[20rem]`. See ARCHITECTURE.md §5.5 for the
  full set of constraints.

## Before considering a change done

- Backend: `cd backend && source .venv/bin/activate && python -m pytest -q`
  must pass (200+ tests).
- Frontend: `cd frontend && npm run build && npm test -- --run && npm run
  lint` must all pass cleanly.
- For security-relevant changes (auth, permissions, external fetches, file
  uploads), also run `bandit -r app -ll` and check against the "accepted
  findings" list in ARCHITECTURE.md §7 before adding new `# nosec`
  annotations.

## Secrets

Never log, commit, or persist real credentials, tokens, or server URLs
(Plex tokens, API keys, etc.) encountered during debugging — sanitise
examples before writing them to code, tests, docs, or commit messages.
