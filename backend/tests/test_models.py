"""Tests for v1 schema constraints (CHECK/UNIQUE/NOT NULL) on Base.metadata."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production")
os.environ.setdefault("COVERS_DIR", "/tmp/armarium_test_covers")
os.environ.setdefault("BACKUP_DIR", "/tmp/armarium_test_backups")

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models  # noqa: F401 — registers ORM tables on Base.metadata
from app.models.enums import LinkMatchType, MediaCategory, Supertype
from app.models.item_link import ItemLink
from app.models.media import MediaItem
from app.models.media_subtype import MediaSubtype
from app.models.platform import Platform
from app.models.plex_config import PlexConfig


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


async def _make_item(session, **overrides) -> MediaItem:
    from sqlalchemy import select

    subtype = (await session.execute(
        select(MediaSubtype).where(MediaSubtype.name == "CD")
    )).scalar_one_or_none()
    if subtype is None:
        subtype = MediaSubtype(name="CD", category=MediaCategory.MUSIC, supertype=Supertype.PHYSICAL)
        session.add(subtype)
        await session.flush()

    defaults = dict(title="Test Item", media_subtype_id=subtype.id)
    defaults.update(overrides)
    item = MediaItem(**defaults)
    session.add(item)
    await session.flush()
    return item


async def test_item_link_requires_ordered_pair(session):
    a = await _make_item(session)
    await session.commit()
    b = await _make_item(session)
    await session.commit()

    session.add(ItemLink(item_a_id=b.id, item_b_id=a.id, matched_via=LinkMatchType.MANUAL))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_item_link_rejects_self_link(session):
    a = await _make_item(session)
    await session.commit()

    session.add(ItemLink(item_a_id=a.id, item_b_id=a.id, matched_via=LinkMatchType.MANUAL))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_item_link_rejects_duplicate_pair(session):
    a = await _make_item(session)
    b = await _make_item(session)
    await session.commit()

    lo, hi = sorted((a.id, b.id))
    session.add(ItemLink(item_a_id=lo, item_b_id=hi, matched_via=LinkMatchType.MANUAL))
    await session.commit()

    session.add(ItemLink(item_a_id=lo, item_b_id=hi, matched_via=LinkMatchType.AUTO))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_media_item_requires_media_subtype(session):
    item = MediaItem(title="No subtype")
    session.add(item)
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_plex_config_is_singleton(session):
    platform = Platform(name="Plex")
    session.add(platform)
    await session.flush()

    session.add(PlexConfig(base_url="https://plex.example.com", token="t1", platform_id=platform.id))
    await session.commit()

    session.add(PlexConfig(base_url="https://plex2.example.com", token="t2", platform_id=platform.id))
    with pytest.raises(IntegrityError):
        await session.commit()
