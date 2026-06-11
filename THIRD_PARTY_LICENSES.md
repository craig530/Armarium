# Third-Party Licences & Attributions

Armarium itself is licensed under the [MIT License](LICENSE). This file lists
the third-party software, fonts, icon sets, brand assets, and external data
sources Armarium uses, along with their licences and any attribution
requirements.

## Summary

Every software dependency in Armarium's direct dependency tree is licensed
under a permissive licence (MIT, BSD, Apache-2.0, ISC, HPND, or PSF-2.0), all
of which are compatible with Armarium's MIT licence — they impose no
copyleft, source-disclosure, or "same licence" requirements on Armarium
itself.

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
| [FastAPI](https://github.com/tiangolo/fastapi) | 0.104.1 | [MIT](https://spdx.org/licenses/MIT.html) | Web framework / API |
| [Uvicorn](https://www.uvicorn.org/) | 0.24.0 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | ASGI server |
| [SQLAlchemy](https://www.sqlalchemy.org) | 2.0.23 | [MIT](https://spdx.org/licenses/MIT.html) | Async ORM / database access |
| [aiosqlite](https://aiosqlite.omnilib.dev) | 0.19.0 | [MIT](https://spdx.org/licenses/MIT.html) | Async SQLite driver |
| [httpx](https://github.com/encode/httpx) | 0.25.2 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | HTTP client for TMDB/MusicBrainz/Open Library |
| [python-multipart](https://github.com/andrew-d/python-multipart) | 0.0.6 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Multipart form parsing (file uploads) |
| [Pillow](https://python-pillow.org) | 10.1.0 | [HPND](https://spdx.org/licenses/HPND.html) | Cover/icon/logo image processing |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.0.0 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Loading `.env` configuration |
| [Pydantic](https://github.com/pydantic/pydantic) | 2.5.2 | [MIT](https://spdx.org/licenses/MIT.html) | Data validation / schemas |
| [pydantic-settings](https://github.com/pydantic/pydantic-settings) | 2.1.0 | [MIT](https://spdx.org/licenses/MIT.html) | Settings management |
| [aiofiles](https://github.com/Tinche/aiofiles) | 23.2.1 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Async file I/O |
| [python-jose](http://github.com/mpdavis/python-jose) | 3.3.0 | [MIT](https://spdx.org/licenses/MIT.html) | JWT signing/verification |
| [passlib](https://passlib.readthedocs.io) | 1.7.4 | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Password hashing |
| [bcrypt](https://github.com/pyca/bcrypt/) | 4.0.1 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | bcrypt hashing backend for passlib |
| [pytest](https://docs.pytest.org/) | 7.4.3 | [MIT](https://spdx.org/licenses/MIT.html) | Test suite (dev only) |
| [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) | 0.23.2 | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Async test support (dev only) |
| [anyio](https://anyio.readthedocs.io/) | 3.7.1 | [MIT](https://spdx.org/licenses/MIT.html) | Async compatibility layer (dev only) |

<details>
<summary>Full installed dependency tree (incl. transitive dependencies)</summary>

Generated with `pip-licenses --format=markdown --with-urls --order=license`
against `backend/.venv`. All licences below are permissive **except**
`certifi` (MPL-2.0, see [Summary](#summary)).

| Package | Version | Licence | URL |
|---|---|---|---|
| aiofiles | 23.2.1 | Apache Software License | https://github.com/Tinche/aiofiles |
| bcrypt | 4.0.1 | Apache Software License | https://github.com/pyca/bcrypt/ |
| pytest-asyncio | 0.23.2 | Apache Software License | https://github.com/pytest-dev/pytest-asyncio |
| rsa | 4.9.1 | Apache Software License | https://stuvel.eu/rsa |
| sniffio | 1.3.1 | Apache Software License; MIT License | https://github.com/python-trio/sniffio |
| uvloop | 0.22.1 | Apache Software License; MIT License | (part of uvicorn[standard]) |
| python-multipart | 0.0.6 | Apache-2.0 | https://github.com/andrew-d/python-multipart |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | https://github.com/pypa/packaging |
| cryptography | 48.0.1 | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography |
| passlib | 1.7.4 | BSD | https://passlib.readthedocs.io |
| click | 8.1.8 | BSD License | https://github.com/pallets/click/ |
| pycparser | 2.23 | BSD License | https://github.com/eliben/pycparser |
| python-dotenv | 1.0.0 | BSD License | https://github.com/theskumar/python-dotenv |
| websockets | 15.0.1 | BSD License | https://github.com/python-websockets/websockets |
| pyasn1 | 0.6.3 | BSD-2-Clause | https://github.com/pyasn1/pyasn1 |
| httpcore | 1.0.9 | BSD-3-Clause | https://www.encode.io/httpcore/ |
| httpx | 0.25.2 | BSD-3-Clause | https://github.com/encode/httpx |
| idna | 3.18 | BSD-3-Clause | https://github.com/kjd/idna |
| starlette | 0.27.0 | BSD-3-Clause | https://github.com/encode/starlette |
| uvicorn | 0.24.0 | BSD-3-Clause | https://www.uvicorn.org/ |
| Pillow | 10.1.0 | Historical Permission Notice and Disclaimer (HPND) | https://python-pillow.org |
| cffi | 2.0.0 | MIT | https://cffi.readthedocs.io/en/latest/whatsnew.html |
| ecdsa | 0.19.2 | MIT | http://github.com/tlsfuzzer/python-ecdsa |
| fastapi | 0.104.1 | MIT | https://github.com/tiangolo/fastapi |
| httptools | 0.8.0 | MIT | https://github.com/MagicStack/httptools |
| iniconfig | 2.1.0 | MIT | https://github.com/pytest-dev/iniconfig |
| pydantic | 2.5.2 | MIT | https://github.com/pydantic/pydantic |
| pydantic-settings | 2.1.0 | MIT | https://github.com/pydantic/pydantic-settings |
| greenlet | 3.2.5 | MIT AND Python-2.0 | https://greenlet.readthedocs.io/ |
| PyYAML | 6.0.3 | MIT License | https://pyyaml.org/ |
| SQLAlchemy | 2.0.23 | MIT License | https://www.sqlalchemy.org |
| aiosqlite | 0.19.0 | MIT License | https://aiosqlite.omnilib.dev |
| annotated-types | 0.7.0 | MIT License | https://github.com/annotated-types/annotated-types |
| anyio | 3.7.1 | MIT License | https://anyio.readthedocs.io/en/stable/versionhistory.html |
| exceptiongroup | 1.3.1 | MIT License | https://github.com/agronholm/exceptiongroup |
| h11 | 0.16.0 | MIT License | https://github.com/python-hyper/h11 |
| pluggy | 1.6.0 | MIT License | https://github.com/pytest-dev/pluggy |
| pydantic_core | 2.14.5 | MIT License | https://github.com/pydantic/pydantic-core |
| pytest | 7.4.3 | MIT License | https://docs.pytest.org/en/latest/ |
| python-jose | 3.3.0 | MIT License | http://github.com/mpdavis/python-jose |
| six | 1.17.0 | MIT License | https://github.com/benjaminp/six |
| watchfiles | 1.1.1 | MIT License | https://github.com/samuelcolvin/watchfiles |
| certifi | 2026.5.20 | Mozilla Public License 2.0 (MPL 2.0) | https://github.com/certifi/python-certifi |
| typing_extensions | 4.15.0 | PSF-2.0 | https://github.com/python/typing_extensions |

To regenerate: `pip install pip-licenses && pip-licenses --format=markdown --with-urls --order=license`

</details>

---

## Frontend dependencies (npm)

### Direct dependencies (`frontend/package.json`)

| Package | Version | Licence | Used for |
|---|---|---|---|
| [React](https://react.dev/) / [react-dom](https://react.dev/) | 18.2.x | [MIT](https://spdx.org/licenses/MIT.html) | UI framework |
| [react-router-dom](https://github.com/remix-run/react-router) | 6.20.x | [MIT](https://spdx.org/licenses/MIT.html) | Client-side routing |
| [Zustand](https://github.com/pmndrs/zustand) | 4.4.x | [MIT](https://spdx.org/licenses/MIT.html) | State management |
| [Axios](https://github.com/axios/axios) | 1.6.x | [MIT](https://spdx.org/licenses/MIT.html) | API client |
| [react-hot-toast](https://github.com/timolins/react-hot-toast) | 2.4.x | [MIT](https://spdx.org/licenses/MIT.html) | Toast notifications |
| [clsx](https://github.com/lukeed/clsx) | 2.0.x | [MIT](https://spdx.org/licenses/MIT.html) | Conditional class names |
| [lucide-react](https://lucide.dev/) | 0.294.x | [ISC](https://spdx.org/licenses/ISC.html) | UI icons & built-in location icons |
| [@zxing/library](https://github.com/zxing-js/library) | 0.20.x | [MIT](https://spdx.org/licenses/MIT.html) | Barcode scanning |

### Build tooling (development only — not shipped in the production bundle)

| Package | Version | Licence | Used for |
|---|---|---|---|
| [Vite](https://vitejs.dev/) | 5.0.x | [MIT](https://spdx.org/licenses/MIT.html) | Build tool / dev server |
| [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react) | 4.2.x | [MIT](https://spdx.org/licenses/MIT.html) | React support for Vite |
| [Tailwind CSS](https://tailwindcss.com/) | 3.3.x | [MIT](https://spdx.org/licenses/MIT.html) | Utility CSS framework |
| [PostCSS](https://postcss.org/) | 8.4.x | [MIT](https://spdx.org/licenses/MIT.html) | CSS processing |
| [Autoprefixer](https://github.com/postcss/autoprefixer) | 10.4.x | [MIT](https://spdx.org/licenses/MIT.html) | CSS vendor prefixing |
| [simple-icons](https://github.com/simple-icons/simple-icons) | 16.23.x | [CC0-1.0](https://spdx.org/licenses/CC0-1.0.html) | Source of bundled platform logo SVGs (see [Platform Logos](#platform-logos)) |

<details>
<summary>Full production dependency tree (incl. transitive dependencies)</summary>

Generated with `npx license-checker --production`. Of the ~45 packages in the
resolved production dependency tree (mostly small transitive utilities pulled
in by axios, react-router and zustand):

- **43 packages** are licensed under the **MIT License**.
- **1 package** (`@zxing/text-encoding`) is dual-licensed
  **(Unlicense OR Apache-2.0)**.
- **1 package** (`lucide-react`) is licensed under **ISC** (see table above).

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
| [Inter](https://rsms.me/inter/) | [SIL Open Font License 1.1](https://spdx.org/licenses/OFL-1.1.html) | Loaded from [Google Fonts](https://fonts.google.com/specimen/Inter) via `<link>` tags in `frontend/index.html` |

The SIL OFL does not require attribution in the application itself, but it is
listed here for transparency. No font files are bundled in this repository —
they are fetched from Google Fonts at runtime.

---

## Icons & Brand Assets

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

---

## Disclaimer

Armarium is independent, open-source software. It is **not affiliated with,
endorsed by, sponsored by, or certified by** TMDB, The Movie Database, MetaBrainz,
MusicBrainz, the Internet Archive, Open Library, or any streaming service,
platform, or brand referenced in its documentation, settings, or user
interface. All product names, logos, and trademarks are the property of their
respective owners and are used in Armarium solely to identify the
corresponding service.
