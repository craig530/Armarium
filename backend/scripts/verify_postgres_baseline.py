"""Verify the Alembic baseline against a real PostgreSQL database.

Exercises the exact startup path `app.main.lifespan` uses for file-based
databases — `AsyncConnection.run_sync(_run_alembic_upgrade)` — against
`DATABASE_URL` (must be a `postgresql+asyncpg://...` URL pointing at an
empty database). Run twice to also check idempotency, then asserts the
seeded media subtypes look right.

Used by the `backend-postgres` CI job (see `.github/workflows/ci.yml`); not
part of the pytest suite, since the rest of the test suite runs against
in-memory SQLite.
"""
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import _run_alembic_upgrade
from app.services.search import setup_fts


async def main() -> None:
    url = os.environ["DATABASE_URL"]
    if "postgresql" not in url:
        sys.exit(f"DATABASE_URL must be a postgresql+asyncpg URL, got: {url!r}")

    engine = create_async_engine(url)
    try:
        for attempt in (1, 2):
            async with engine.connect() as conn:
                await conn.run_sync(_run_alembic_upgrade)
                await conn.commit()
            print(f"alembic upgrade head: OK (attempt {attempt})")

        async with engine.begin() as conn:
            await setup_fts(conn)
        print("setup_fts: OK (no-op on non-SQLite)")

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT category, supertype, name FROM media_subtypes"))
            rows = result.all()

        assert len(rows) == 16, f"expected 16 seeded media subtypes, got {len(rows)}: {rows}"
        categories = {row[0] for row in rows}
        assert categories == {"MUSIC", "FILMS_TV", "BOOKS", "GAMES"}, categories
        print(f"media_subtypes seed: OK ({len(rows)} rows)")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
