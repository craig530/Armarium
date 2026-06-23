# Third-Party Licences & Attributions

Armarium itself is licensed under the [MIT License](LICENSE). This file lists
the third-party software, fonts, icon sets, brand assets, and external data
sources Armarium uses, along with their licences and any attribution
requirements.

## Summary

Every software dependency in Armarium's direct dependency tree is licensed
under a permissive licence (MIT, BSD, Apache-2.0, ISC, MIT-CMU, PSF-2.0, or
Unlicense), all of which are compatible with Armarium's MIT licence — they
impose no copyleft, source-disclosure, or "same licence" requirements on
Armarium itself.

One transitive dependency, **certifi** (used internally by `httpx`), is
licensed under the **Mozilla Public License 2.0**. MPL-2.0 is a file-level
("weak") copyleft licence: it only requires that *modifications to certifi's
own files* be shared under MPL-2.0. Armarium uses certifi unmodified as an
ordinary dependency, which does not affect Armarium's licensing — this is the
same situation as virtually every Python project that makes HTTPS requests.

**No dependency in this project is licensed under GPL, LGPL, AGPL, EUPL, or a
proprietary licence**, so no replacements are needed on licence-compatibility
grounds.

Brand logos and trademarks (TMDB, MusicBrainz, streaming/platform logos, etc.)
are **not** covered by Armarium's MIT licence — see
[External Data Sources & APIs](#external-data-sources--apis) and
[Platform Logos](#platform-logos) below.

---

## Backend dependencies (Python)

### Direct dependencies (`backend/requirements.txt`)

| Package | Version | Licence | Used for |
|---|---|---|---|
| [FastAPI](https://github.com/fastapi/fastapi) | 0.136.3 | [MIT](https://spdx.org/licenses/MIT.html) | Web framework / API |
| [Uvicorn](https://www.uvicorn.org/) | 0.24.0 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | ASGI server |
| [SQLAlchemy](https://www.sqlalchemy.org) | 2.0.50 | [MIT](https://spdx.org/licenses/MIT.html) | Async ORM / database access |
| [Alembic](https://alembic.sqlalchemy.org) | 1.18.4 | [MIT](https://spdx.org/licenses/MIT.html) | Database schema migrations |
| [aiosqlite](https://aiosqlite.omnilib.dev) | 0.19.0 | [MIT](https://spdx.org/licenses/MIT.html) | Async SQLite driver |
| [asyncpg](https://github.com/MagicStack/asyncpg) | 0.30.0 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Optional PostgreSQL driver (see [Advanced: Using PostgreSQL](README.md#advanced-using-postgresql)) |
| [httpx](https://github.com/encode/httpx) | 0.28.1 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | HTTP client for TMDB/MusicBrainz/Open Library |
| [python-multipart](https://github.com/Kludex/python-multipart) | 0.0.31 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Multipart form parsing (file uploads) |
| [Pillow](https://python-pillow.github.io) | 12.2.0 | [MIT-CMU](https://spdx.org/licenses/MIT-CMU.html) | Cover/icon/logo image processing |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.2 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Loading `.env` configuration |
| [Pydantic](https://github.com/pydantic/pydantic) | 2.13.4 | [MIT](https://spdx.org/licenses/MIT.html) | Data validation / schemas |
| [pydantic-settings](https://github.com/pydantic/pydantic-settings) | 2.14.1 | [MIT](https://spdx.org/licenses/MIT.html) | Settings management |
| [email-validator](https://github.com/JoshData/python-email-validator) | 2.3.0 | [Unlicense](https://spdx.org/licenses/Unlicense.html) | Email address validation (Pydantic `EmailStr`, used by user invites) |
| [aiofiles](https://github.com/Tinche/aiofiles) | 23.2.1 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Async file I/O |
| [APScheduler](https://github.com/agronholm/apscheduler) | 3.10.4 | [MIT](https://spdx.org/licenses/MIT.html) | In-process background job scheduling (Plex sync, maintenance tasks) |
| [zxing-cpp](https://github.com/zxing-cpp/zxing-cpp) | 3.0.0 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Server-side barcode decoding for the camera scanner |
| [python-jose](http://github.com/mpdavis/python-jose) | 3.5.0 | [MIT](https://spdx.org/licenses/MIT.html) | JWT signing/verification |
| [passlib](https://passlib.readthedocs.io) | 1.7.4 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Password hashing |
| [bcrypt](https://github.com/pyca/bcrypt/) | 4.0.1 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | bcrypt hashing backend for passlib |
| [pytest](https://docs.pytest.org/) | 9.1.0 | [MIT](https://spdx.org/licenses/MIT.html) | Test suite (dev only) |
| [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) | 1.4.0 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Async test support (dev only) |
| [anyio](https://anyio.readthedocs.io/) | 4.13.0 | [MIT](https://spdx.org/licenses/MIT.html) | Async compatibility layer (dev only) |
| [ruff](https://docs.astral.sh/ruff) | 0.15.17 | [MIT](https://spdx.org/licenses/MIT.html) | Linting (dev/CI only) |
| [bandit](https://bandit.readthedocs.io/) | 1.9.4 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | SAST scanning (dev/CI only) |
| [pip-audit](https://pypi.org/project/pip-audit/) | 2.10.1 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Dependency CVE scanning (dev/CI only) |

<details>
<summary>Full installed dependency tree (incl. transitive dependencies)</summary>

Generated with `pip-licenses --format=markdown --with-urls --order=license`
against a clean `pip install -r backend/requirements.txt` (production
dependencies only). All licences below are permissive **except** `certifi`
(MPL-2.0, see [Summary](#summary)).

Dev/CI-only tooling (`requirements-dev.txt`: pytest, pytest-asyncio, anyio,
ruff, bandit, pip-audit) and its own transitive dependencies are not shipped
in the production image and so are excluded from this table — all of them
are likewise MIT, BSD, Apache-2.0, or PSF-licensed.

| Package | Version | Licence | URL |
|---|---|---|---|
| aiofiles | 23.2.1 | Apache Software License | https://github.com/Tinche/aiofiles |
| asyncpg | 0.30.0 | Apache Software License | https://github.com/MagicStack/asyncpg |
| bcrypt | 4.0.1 | Apache Software License | https://github.com/pyca/bcrypt/ |
| rsa | 4.9.1 | Apache Software License | https://stuvel.eu/rsa |
| uvloop | 0.22.1 | Apache Software License; MIT License | (part of uvicorn[standard]) |
| python-multipart | 0.0.31 | Apache-2.0 | https://github.com/Kludex/python-multipart |
| zxing-cpp | 3.0.0 | Apache-2.0 | https://github.com/zxing-cpp/zxing-cpp |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography |
| passlib | 1.7.4 | BSD | https://passlib.readthedocs.io |
| httpx | 0.28.1 | BSD License | https://github.com/encode/httpx |
| pyasn1 | 0.6.3 | BSD-2-Clause | https://github.com/pyasn1/pyasn1 |
| MarkupSafe | 3.0.3 | BSD-3-Clause | https://github.com/pallets/markupsafe/ |
| click | 8.4.1 | BSD-3-Clause | https://github.com/pallets/click/ |
| httpcore | 1.0.9 | BSD-3-Clause | https://www.encode.io/httpcore/ |
| idna | 3.18 | BSD-3-Clause | https://github.com/kjd/idna |
| pycparser | 3.0 | BSD-3-Clause | https://github.com/eliben/pycparser |
| python-dotenv | 1.2.2 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| starlette | 1.3.1 | BSD-3-Clause | https://github.com/Kludex/starlette |
| uvicorn | 0.24.0 | BSD-3-Clause | https://www.uvicorn.org/ |
| websockets | 16.0 | BSD-3-Clause | https://github.com/python-websockets/websockets |
| dnspython | 2.8.0 | ISC License (ISCL) | https://www.dnspython.org |
| SQLAlchemy | 2.0.50 | MIT | https://www.sqlalchemy.org |
| alembic | 1.18.4 | MIT | https://alembic.sqlalchemy.org |
| annotated-doc | 0.0.4 | MIT | https://github.com/fastapi/annotated-doc |
| anyio | 4.13.0 | MIT | https://anyio.readthedocs.io/en/stable/versionhistory.html |
| cffi | 2.0.0 | MIT | https://cffi.readthedocs.io/en/latest/whatsnew.html |
| ecdsa | 0.19.2 | MIT | http://github.com/tlsfuzzer/python-ecdsa |
| fastapi | 0.136.3 | MIT | https://github.com/fastapi/fastapi |
| httptools | 0.8.0 | MIT | https://github.com/MagicStack/httptools |
| pydantic | 2.13.4 | MIT | https://github.com/pydantic/pydantic |
| pydantic-settings | 2.14.1 | MIT | https://github.com/pydantic/pydantic-settings |
| pydantic_core | 2.46.4 | MIT | https://github.com/pydantic |
| typing-inspection | 0.4.2 | MIT | https://github.com/pydantic/typing-inspection |
| greenlet | 3.5.1 | MIT AND PSF-2.0 | https://greenlet.readthedocs.io |
| Mako | 1.3.12 | MIT License | https://www.makotemplates.org/ |
| PyYAML | 6.0.3 | MIT License | https://pyyaml.org/ |
| aiosqlite | 0.19.0 | MIT License | https://aiosqlite.omnilib.dev |
| annotated-types | 0.7.0 | MIT License | https://github.com/annotated-types/annotated-types |
| h11 | 0.16.0 | MIT License | https://github.com/python-hyper/h11 |
| python-jose | 3.5.0 | MIT License | http://github.com/mpdavis/python-jose |
| six | 1.17.0 | MIT License | https://github.com/benjaminp/six |
| watchfiles | 1.2.0 | MIT License | https://github.com/samuelcolvin/watchfiles |
| pillow | 12.2.0 | MIT-CMU | https://python-pillow.github.io |
| certifi | 2026.5.20 | Mozilla Public License 2.0 (MPL 2.0) | https://github.com/certifi/python-certifi |
| typing_extensions | 4.15.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| email-validator | 2.3.0 | The Unlicense (Unlicense) | https://github.com/JoshData/python-email-validator |

To regenerate: create a clean virtualenv, `pip install -r backend/requirements.txt pip-licenses`,
then `pip-licenses --format=markdown --with-urls --order=license`.

</details>

---

## Frontend dependencies (npm)

### Direct dependencies (`frontend/package.json`)

| Package | Version | Licence | Used for |
|---|---|---|---|
| [React](https://react.dev/) / [react-dom](https://react.dev/) | 19.2.x | [MIT](https://spdx.org/licenses/MIT.html) | UI framework |
| [react-router-dom](https://github.com/remix-run/react-router) | 7.17.x | [MIT](https://spdx.org/licenses/MIT.html) | Client-side routing |
| [Zustand](https://github.com/pmndrs/zustand) | 5.0.x | [MIT](https://spdx.org/licenses/MIT.html) | State management |
| [Axios](https://github.com/axios/axios) | 1.17.x | [MIT](https://spdx.org/licenses/MIT.html) | API client |
| [react-hot-toast](https://github.com/timolins/react-hot-toast) | 2.6.x | [MIT](https://spdx.org/licenses/MIT.html) | Toast notifications |
| [clsx](https://github.com/lukeed/clsx) | 2.1.x | [MIT](https://spdx.org/licenses/MIT.html) | Conditional class names |
| [lucide-react](https://lucide.dev/) | 1.18.x | [ISC](https://spdx.org/licenses/ISC.html) | UI icons & built-in location icons |
| [react-barcode](https://github.com/kciter/react-barcode) | 1.6.x | [ISC](https://spdx.org/licenses/ISC.html) | Renders an item's barcode as a scannable image on its detail page |
| [jsbarcode](https://github.com/lindell/JsBarcode) | 3.12.x | [MIT](https://spdx.org/licenses/MIT.html) | Barcode rendering engine used by react-barcode |

Barcode *scanning* is decoded server-side via
[zxing-cpp](#backend-dependencies-python). react-barcode/jsbarcode are used
only to *display* an already-known barcode value as an image — both render
client-side to an inline SVG, with no network fetches.

### Build tooling (development only — not shipped in the production bundle)

| Package | Version | Licence | Used for |
|---|---|---|---|
| [Vite](https://vitejs.dev/) | 8.0.x | [MIT](https://spdx.org/licenses/MIT.html) | Build tool / dev server |
| [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react) | 6.0.x | [MIT](https://spdx.org/licenses/MIT.html) | React support for Vite |
| [Tailwind CSS](https://tailwindcss.com/) | 4.3.x | [MIT](https://spdx.org/licenses/MIT.html) | Utility CSS framework |
| [@tailwindcss/postcss](https://github.com/tailwindlabs/tailwindcss) | 4.3.x | [MIT](https://spdx.org/licenses/MIT.html) | PostCSS plugin for Tailwind CSS v4 (includes vendor prefixing) |
| [PostCSS](https://postcss.org/) | 8.5.x | [MIT](https://spdx.org/licenses/MIT.html) | CSS processing |
| [simple-icons](https://github.com/simple-icons/simple-icons) | 16.23.x | [CC0-1.0](https://spdx.org/licenses/CC0-1.0.html) | Source of bundled platform logo SVGs (see [Platform Logos](#platform-logos)) |

<details>
<summary>Full production dependency tree (incl. transitive dependencies)</summary>

Generated with `npx license-checker --production`. Of the 47 third-party
packages in the resolved production dependency tree (mostly small transitive
utilities pulled in by axios, react-router and zustand):

- **45 packages** are licensed under the **MIT License**.
- **2 packages** (`lucide-react`, `react-barcode`) are licensed under **ISC**
  (see table above).

No GPL, LGPL, AGPL, MPL, or proprietary-licensed packages appear anywhere in
the frontend production dependency tree.

To regenerate the full itemised list:

```bash
cd frontend
npx license-checker --production
```

</details>

---

## Fonts

| Font | Licence | Source |
|---|---|---|
| [Inter](https://rsms.me/inter/) | [SIL Open Font License 1.1](https://spdx.org/licenses/OFL-1.1.html) | Self-hosted via [@fontsource/inter](https://www.npmjs.com/package/@fontsource/inter), imported in `frontend/src/main.jsx` |
| [Fraunces](https://github.com/undercasetype/Fraunces) | [SIL Open Font License 1.1](https://spdx.org/licenses/OFL-1.1.html) | Self-hosted via [@fontsource/fraunces](https://www.npmjs.com/package/@fontsource/fraunces), imported in `frontend/src/main.jsx`; used for headings and the wordmark |

The SIL OFL does not require attribution in the application itself, but it is
listed here for transparency. Font files are bundled with the frontend build
(via the `@fontsource` packages) rather than fetched from Google Fonts at
runtime — this keeps the app fully self-contained and compatible with the
strict `style-src`/`font-src` Content-Security-Policy
(`frontend/nginx/security-headers.conf`).

---

## Icons & Brand Assets

### Armarium logo

The Armarium logo and wordmark (`frontend/src/assets/brand/armarium-logo.svg`,
plus its generated favicon and PWA icon variants — `favicon.svg`,
`icon-192.png`, `icon-512.png`, `apple-touch-icon.png`) are original artwork
created for this project and are covered by the project's MIT licence, not by
any third-party licence.

### Location icons

The built-in location icon set (`frontend/src/lib/locationIcons.js`) uses
icons from [Lucide](https://lucide.dev/) (`lucide-react`, ISC licence — see
[Frontend dependencies](#frontend-dependencies-npm)). These are generic,
non-trademarked symbols (bookshelf, box, drawer, etc.) and require no
additional attribution beyond the standard package licence.

### Platform logos

Built-in platform logos (`frontend/src/assets/icons/platforms/*.svg`) are
extracted at build time from [simple-icons](https://github.com/simple-icons/simple-icons)
(`frontend/scripts/extract-platform-logos.mjs`), currently covering: Plex,
Netflix, Apple TV, Spotify, Apple Music, YouTube Music, Tidal, MUBI, NOW,
Paramount+, HBO Max/Max, Crunchyroll, Audible, Google Play, YouTube, Bandcamp,
SoundCloud, Deezer, iTunes, Sky, and Rakuten TV.

The simple-icons **package** (the SVG path data and code that ships it) is
released under **CC0-1.0** (public domain). However, **the brand marks
themselves — the Netflix logo, Spotify logo, and so on — remain the
registered trademarks of their respective owners** (Netflix, Inc.; Spotify
AB; Apple Inc.; The Walt Disney Company; Warner Bros. Discovery; etc.). CC0
applies to simple-icons' redistribution of the icon *files*; it does not
grant any trademark rights.

**Use in Armarium:** these logos are used solely so that a user can visually
identify which streaming or digital platform they've linked an item to in
*their own private catalogue* — a small, fixed-size logo next to a
user-created "Platform" entry. This is a textbook case of **nominative fair
use**: identifying a third-party product/service by its own mark, with no
implication of sponsorship, affiliation, or endorsement by that company.
Armarium is not affiliated with, endorsed by, or sponsored by any of the
platforms whose logos may appear:

> Plex, Netflix, Amazon Prime Video, Apple TV, Disney+, Spotify, Apple Music,
> YouTube Music, Tidal, Qobuz, MUBI, BFI Player, NOW (NOW TV), Paramount+,
> Peacock, HBO Max (Max), Crunchyroll, Audible, Kindle, Google Play, YouTube,
> Bandcamp, SoundCloud, Deezer, iTunes, Sky, Rakuten TV, and Curzon Home
> Cinema are trademarks of their respective owners. References to these
> services in Armarium are for identification purposes only.

A handful of platforms in `frontend/src/lib/platformLogos.js`
(**Amazon Prime Video, Disney+, Qobuz, BFI Player, Peacock, Kindle, Curzon
Home Cinema**) have no official entry in simple-icons and have no bundled
brand asset. These fall back to a generated letter-mark badge (the
platform's initials on a deterministic accent colour, see
`frontend/src/components/ui/PlatformLogo.jsx`) rather than any third-party
logo.

> **Maintenance note:** "HBO Max" was rebranded to "Max" in 2023. The
> `simple-icons` entry used here (`siHbomax`) reflects the version of
> simple-icons pinned in `package.json` (16.23.x) at the time of this audit.
> If simple-icons renames or removes this icon in a future major version,
> re-run `extract-platform-logos.mjs` after updating the mapping in
> `PLATFORM_ICON_SOURCES`.

### TMDB logo

`frontend/src/assets/tmdb/blue_short.svg`, `blue_square_1.svg` and
`blue_square_2.svg` are official logo assets for
[The Movie Database (TMDB)](https://www.themoviedb.org/), obtained from
TMDB's [logo & attribution page](https://www.themoviedb.org/about/logos-attribution).
These are **TMDB trademarks**, not Armarium's own assets, and are **not**
covered by the MIT licence — they are included solely to satisfy TMDB's API
attribution requirements. See
[TMDB (The Movie Database)](#tmdb-the-movie-database) below for the full
attribution text and usage notes.

---

## External Data Sources & APIs

Armarium is **not affiliated with, endorsed by, or certified by** any of the
following services. They are independent third-party data sources that
Armarium's users may optionally connect to for metadata lookup.

### TMDB (The Movie Database)

Used for Films & TV metadata and cover art (`backend/app/services/tmdb.py`).

- **Required attribution (verbatim, per TMDB's API Terms of Use):**
  > This product uses the TMDB API but is not endorsed or certified by TMDB.
- This text, alongside TMDB's official "blue short" logo, is shown in the app
  footer and on Films & TV item pages and edition pickers — see
  `frontend/src/components/ui/TMDBAttribution.jsx`. The logo assets (sourced
  from TMDB's [logo & attribution page](https://www.themoviedb.org/about/logos-attribution))
  are bundled under `frontend/src/assets/tmdb/`
  (`blue_short.svg`, `blue_square_1.svg`, `blue_square_2.svg`).
- **TMDB's logo is a trademark of TMDB and is not covered by Armarium's MIT
  licence.** It is included solely to satisfy TMDB's API attribution
  requirement and must not be modified, recoloured, or used in a way that
  implies endorsement — see TMDB's
  [logo & attribution guidelines](https://www.themoviedb.org/about/logos-attribution)
  for permitted usage.
- **API key handling:** `TMDB_API_KEY` is read server-side only
  (`backend/app/config.py`) and is never sent to the frontend or exposed in
  responses, satisfying TMDB's requirement not to expose API keys publicly.
- **Caching:** search/lookup results are cached in-process for 1–2 hours
  (`backend/app/services/cache.py`), and poster images are downloaded once
  and stored locally (`backend/app/services/cover_art.py`) rather than
  hot-linked on every page view.
- **Scope of use:** Armarium is a personal, self-hosted catalogue for a
  user's own collection — not a public database or aggregator built on TMDB
  data. If you operate a hosted/multi-tenant Armarium instance as a
  commercial service, review TMDB's terms separately, as they distinguish
  personal/non-commercial use from commercial use.

### MusicBrainz / MetaBrainz

Used for Music metadata (`backend/app/services/musicbrainz.py`), including
cover art via the [Cover Art Archive](https://coverartarchive.org/) (hosted
by the Internet Archive on MetaBrainz's behalf).

- MusicBrainz's database is dedicated to the public domain
  ([CC0](https://spdx.org/licenses/CC0-1.0.html)), but the
  [MetaBrainz API terms](https://musicbrainz.org/doc/MusicBrainz_API) ask
  that applications credit **MusicBrainz** (linking to
  [musicbrainz.org](https://musicbrainz.org/)) as the data source. This
  credit is included in the app footer.
- MetaBrainz's API guidelines require a descriptive `User-Agent` header
  identifying the application and ideally a contact URL. Armarium's
  `User-Agent` has been updated to include a link back to this project's
  repository (`backend/app/services/musicbrainz.py`).
- MetaBrainz's documented rate limit for unauthenticated use is approximately
  **1 request/second per IP**. Armarium caches lookup results for 1–2 hours
  and rate-limits each user to 30 lookup requests/minute
  (`backend/app/api/v1/lookup.py`), which keeps typical single/few-user
  deployments well within this limit. **Flag:** with several users searching
  *simultaneously*, combined outbound traffic could briefly exceed 1 req/sec
  — for larger multi-user deployments, consider adding a global outbound
  throttle in `musicbrainz.py`.
- Cover Art Archive images are cached locally after first download, the same
  as TMDB/Open Library covers.

### Open Library / Internet Archive

Used for Books metadata (`backend/app/services/openlibrary.py`), via the
Open Library [Books API](https://openlibrary.org/dev/docs/api/books) and
[Covers API](https://openlibrary.org/dev/docs/api/covers).

- Open Library is a project of the [Internet Archive](https://archive.org/),
  a registered non-profit. Its API is free to use without an API key.
  Armarium credits **Open Library** (linking to
  [openlibrary.org](https://openlibrary.org/)) in the app footer.
- Open Library's API guidelines ask for a descriptive `User-Agent` header.
  Armarium's `User-Agent` has been updated to include a link back to this
  project's repository (`backend/app/services/openlibrary.py`).
- Open Library asks high-volume consumers to cache cover images rather than
  hot-linking them on every request — Armarium downloads and caches covers
  locally (`backend/app/services/cover_art.py`), so this is already
  satisfied.
- Bibliographic metadata (title, author, ISBN, publisher, etc.) returned by
  Open Library is largely factual/catalogue data; cover images are provided
  by Open Library specifically for this kind of referential, non-commercial
  use.

### IGDB (Internet Game Database)

Used for Games metadata and cover art (`backend/app/services/igdb.py`), via
the [IGDB API](https://api-docs.igdb.com/) (operated by Twitch Interactive, Inc.).

- **API authentication:** IGDB requires a Twitch developer account and OAuth2
  credentials (`IGDB_CLIENT_ID` + `IGDB_CLIENT_SECRET`) to generate a bearer
  token. Credentials are read server-side only (`backend/app/config.py`) and
  are never sent to the frontend or exposed in API responses. Tokens are
  cached in-process and refreshed on expiry.
- **Attribution:** Armarium displays the IGDB logo on Games item pages and the
  game search picker — see `frontend/src/components/ui/IGDBAttribution.jsx`.
  The logo is sourced from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:IGDB_logo.svg)
  and is bundled under `frontend/src/assets/igdb/logo.svg`. The Wikimedia
  Commons file is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **IGDB's brand assets are trademarks of Twitch Interactive, Inc. and are
  not covered by Armarium's MIT licence.** They are included solely for
  attribution purposes and must not be modified or used in a way that
  implies endorsement by Twitch or IGDB.
- **Caching:** search/lookup results are cached in-process for 1–2 hours
  (`backend/app/services/cache.py`), and game cover images are downloaded once
  and stored locally (`backend/app/services/cover_art.py`) rather than
  hot-linked on every page view.
- **Scope of use:** Armarium is a personal, self-hosted catalogue for a user's
  own collection. If you operate a hosted/multi-tenant instance, review
  IGDB's [API terms of service](https://www.igdb.com/api_terms_of_use) separately.

### UPCitemdb & UPCDatabase.org

Neither TMDB nor IGDB support looking up a title by barcode, so the Films &
TV and Games barcode-scan flows (`backend/app/services/upc.py`) first resolve
a product title from a barcode via these two services, then search
TMDB/IGDB by that title:

- **[UPCitemdb](https://www.upcitemdb.com/)** — queried first, via its free
  trial endpoint (`api.upcitemdb.com/prod/trial/lookup`). No API key or
  attribution requirement; used purely as an internal lookup step — no
  UPCitemdb branding, data, or links are shown to the user.
- **[UPCDatabase.org](https://upcdatabase.org/)** — optional second fallback,
  only queried if UPCitemdb has no match and `UPCDATABASE_API_KEY` is set in
  `.env`. Same internal-lookup-only usage as UPCitemdb; no attribution
  requirement found in its terms.
- Neither service's product titles or descriptions are stored or displayed
  verbatim — they're cleaned (`upc._clean_title()`) and used only as a search
  query against TMDB/IGDB, whose own results (and licensing/attribution
  obligations, documented above) are what's actually shown to the user.

### IGDB logo

The file `frontend/src/assets/igdb/logo.svg` is sourced from the IGDB logo
uploaded to [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:IGDB_logo.svg).
The Wikimedia Commons file is published under the
[Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/)
licence. It is used here for identification and attribution purposes only, in
accordance with that licence.

---

## Disclaimer

Armarium is independent, open-source software. It is **not affiliated with,
endorsed by, sponsored by, or certified by** TMDB, The Movie Database, MetaBrainz,
MusicBrainz, the Internet Archive, Open Library, IGDB, Twitch, UPCitemdb,
UPCDatabase.org, or any streaming service, platform, retail, console,
publisher brand, or other brand referenced in its documentation, settings, or
user interface. All product names, logos, and trademarks are the property of
their respective owners and are used in Armarium solely to identify the
corresponding service.
