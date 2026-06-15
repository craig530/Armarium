from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from typing import Optional
import math

from ...database import AsyncSessionLocal
from ...models.media import MediaItem
from ...models.enums import LinkMatchType, MediaCategory, Supertype
from ...repositories.location import LocationRepository, get_location_repository
from ...repositories.media_item import MediaItemRepository, get_media_item_repository
from ...schemas.media import (
    MediaItemCreate, MediaItemUpdate, MediaItemResponse, MediaListResponse, LibraryStats,
    MediaSubtypeSummary, PlatformSummary, LinkedItemSummary, ItemLinkCreate,
)
from ...services.cover_art import download_cover, cover_urls, delete_cover_files, optimise_and_save
from ...services.auth import get_current_user, require_permission

router = APIRouter()

ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_COVER_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


async def _link_summaries(
    repo: MediaItemRepository,
    item_ids: list,
    subtype_map: dict,
    platform_map: dict,
    path_map: dict,
    icon_map: dict,
) -> dict:
    link_map = await repo.link_map(item_ids)
    if not link_map:
        return {}

    all_partner_ids = {pid for partner_ids in link_map.values() for pid in partner_ids}
    partners = await repo.get_by_ids(all_partner_ids)
    partner_by_id = {p.id: p for p in partners}

    def _summary(partner: MediaItem):
        subtype_info = subtype_map.get(partner.media_subtype_id)
        if subtype_info is None:
            return None

        platform_info = platform_map.get(partner.platform_id)
        icon_info = icon_map.get(partner.location_id, {})
        cover_url, cover_thumb_url = cover_urls(partner.cover_image_path, partner.cover_image_url)

        return LinkedItemSummary(
            id=partner.id,
            title=partner.title,
            cover_url=cover_url,
            cover_thumb_url=cover_thumb_url,
            media_subtype=MediaSubtypeSummary(**subtype_info),
            category=subtype_info["category"],
            supertype=subtype_info["supertype"],
            location_id=partner.location_id,
            location_name=partner.location.name if partner.location else None,
            location_path=path_map.get(partner.location_id) if partner.location_id is not None else None,
            location_icon_key=icon_info.get("icon_key"),
            location_icon_url=icon_info.get("icon_url"),
            platform=PlatformSummary(**platform_info) if platform_info else None,
        )

    summaries: dict = {}
    for item_id, partner_ids in link_map.items():
        result = []
        for partner_id in partner_ids:
            partner = partner_by_id.get(partner_id)
            if partner is None:
                continue
            summary = _summary(partner)
            if summary is not None:
                result.append(summary)
        if result:
            summaries[item_id] = result
    return summaries


def _item_to_response(
    item: MediaItem,
    path_map: dict,
    subtype_map: dict,
    platform_map: dict,
    icon_map: dict,
    link_summaries: dict,
) -> MediaItemResponse:
    cover_url, cover_thumb_url = cover_urls(item.cover_image_path, item.cover_image_url)

    subtype_info = subtype_map.get(item.media_subtype_id)
    platform_info = platform_map.get(item.platform_id)
    icon_info = icon_map.get(item.location_id, {})
    linked = link_summaries.get(item.id, [])

    own_supertype = subtype_info["supertype"] if subtype_info else None
    group_supertypes = {link.supertype for link in linked}
    if own_supertype is not None:
        group_supertypes.add(own_supertype)

    if Supertype.PHYSICAL in group_supertypes and Supertype.DIGITAL in group_supertypes:
        ownership = "both"
    elif own_supertype is not None:
        ownership = own_supertype.value
    else:
        ownership = "physical"

    return MediaItemResponse(
        **{
            col: getattr(item, col)
            for col in [
                "id", "title", "year", "genres", "description",
                "cover_image_path", "cover_image_url", "barcode", "edition", "notes", "user_rating",
                "artist", "label", "track_count", "director", "studio",
                "runtime_minutes", "rating", "tmdb_rating", "cast_list", "seasons_owned", "episode_count",
                "author", "publisher", "page_count", "isbn", "language",
                "musicbrainz_id", "tmdb_id", "openlibrary_id",
                "media_subtype_id", "location_id", "platform_id",
                "created_at", "updated_at",
            ]
        },
        cover_url=cover_url,
        cover_thumb_url=cover_thumb_url,
        media_subtype=MediaSubtypeSummary(**subtype_info) if subtype_info else None,
        category=subtype_info["category"] if subtype_info else None,
        supertype=subtype_info["supertype"] if subtype_info else None,
        location_name=item.location.name if item.location else None,
        location_path=path_map.get(item.location_id) if item.location_id is not None else None,
        location_icon_key=icon_info.get("icon_key"),
        location_icon_url=icon_info.get("icon_url"),
        platform=PlatformSummary(**platform_info) if platform_info else None,
        linked_items=linked,
        ownership=ownership,
    )


async def _build_responses(repo: MediaItemRepository, items: list) -> list:
    path_map, icon_map = await repo.location_maps()
    subtype_map = await repo.subtype_map()
    platform_map = await repo.platform_map()
    item_ids = [i.id for i in items]
    link_summaries = await _link_summaries(repo, item_ids, subtype_map, platform_map, path_map, icon_map)
    return [
        _item_to_response(i, path_map, subtype_map, platform_map, icon_map, link_summaries)
        for i in items
    ]


async def _build_response(repo: MediaItemRepository, item: MediaItem) -> MediaItemResponse:
    return (await _build_responses(repo, [item]))[0]


@router.get("", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    q: Optional[str] = None,
    category: Optional[MediaCategory] = None,
    supertype: Optional[Supertype] = None,
    media_subtype_id: Optional[int] = None,
    platform_id: Optional[int] = None,
    genre: Optional[str] = None,
    year: Optional[int] = None,
    location_id: Optional[int] = None,
    sort: str = Query("created_at", pattern="^(title|year|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    _=Depends(get_current_user),
    repo: MediaItemRepository = Depends(get_media_item_repository),
    location_repo: LocationRepository = Depends(get_location_repository),
):
    location_ids = await location_repo.descendant_ids(location_id) if location_id else None
    items, total = await repo.search(
        q=q, category=category, supertype=supertype, media_subtype_id=media_subtype_id,
        platform_id=platform_id, genre=genre, year=year, location_ids=location_ids,
        sort=sort, order=order, page=page, per_page=per_page,
    )

    return MediaListResponse(
        items=await _build_responses(repo, items),
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


def _validate_ownership_fields(supertype: Supertype, location_id: Optional[int], platform_id: Optional[int]) -> None:
    if supertype == Supertype.PHYSICAL and platform_id is not None:
        raise HTTPException(status_code=400, detail="Physical items cannot have a platform")
    if supertype == Supertype.DIGITAL and location_id is not None:
        raise HTTPException(status_code=400, detail="Digital items cannot have a location")


async def _fetch_cover_in_background(item_id: int, url: str) -> None:
    """Download + optimise a cover image and attach it to the item.

    Runs after the response has been sent (via `BackgroundTasks`) so cover
    downloads never add latency to create/update requests. Uses its own
    session since the request's session is closed by the time this runs.
    Until this completes, `cover_url` falls back to the remote
    `cover_image_url`.
    """
    local_path = await download_cover(url, item_id)
    if not local_path:
        return
    async with AsyncSessionLocal() as db:
        repo = MediaItemRepository(db)
        await repo.set_cover_path(item_id, local_path)
        await repo.commit()


@router.post("", response_model=MediaItemResponse, status_code=201)
async def create_media(
    payload: MediaItemCreate,
    background_tasks: BackgroundTasks,
    _=Depends(require_permission("can_add_items")),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    subtype = await repo.resolve_subtype(payload.media_subtype_id)
    await repo.check_location_exists(payload.location_id)
    await repo.check_platform_exists(payload.platform_id)
    _validate_ownership_fields(subtype.supertype, payload.location_id, payload.platform_id)

    item = MediaItem(**payload.model_dump())
    repo.add(item)
    await repo.flush()

    if item.cover_image_url:
        background_tasks.add_task(_fetch_cover_in_background, item.id, item.cover_image_url)

    await repo.commit()
    await repo.auto_link_item(item, subtype)

    item = await repo.reload(item.id)
    return await _build_response(repo, item)


@router.get("/stats", response_model=LibraryStats)
async def get_stats(_=Depends(get_current_user), repo: MediaItemRepository = Depends(get_media_item_repository)):
    return LibraryStats(
        total=await repo.count_total(),
        by_category=await repo.count_by_category(),
        by_supertype=await repo.count_by_supertype(),
        by_subtype=await repo.count_by_subtype(),
        recent_additions=await _build_responses(repo, await repo.recent(6)),
    )


@router.post("/link", response_model=MediaItemResponse, status_code=201)
async def link_items(
    payload: ItemLinkCreate,
    _=Depends(require_permission("can_add_items")),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    if payload.item_a_id == payload.item_b_id:
        raise HTTPException(status_code=400, detail="Cannot link an item to itself")

    existing_ids = await repo.ids_exist([payload.item_a_id, payload.item_b_id])
    if payload.item_a_id not in existing_ids or payload.item_b_id not in existing_ids:
        raise HTTPException(status_code=404, detail="Item not found")

    if await repo.get_link(payload.item_a_id, payload.item_b_id) is not None:
        raise HTTPException(status_code=400, detail="These items are already linked")

    repo.create_link(payload.item_a_id, payload.item_b_id, LinkMatchType.MANUAL)
    await repo.commit()

    item_a = await repo.reload(payload.item_a_id)
    return await _build_response(repo, item_a)


@router.get("/{item_id}", response_model=MediaItemResponse)
async def get_media(item_id: int, _=Depends(get_current_user), repo: MediaItemRepository = Depends(get_media_item_repository)):
    item = await repo.get_with_location(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return await _build_response(repo, item)


@router.put("/{item_id}", response_model=MediaItemResponse)
async def update_media(
    item_id: int,
    payload: MediaItemUpdate,
    background_tasks: BackgroundTasks,
    _=Depends(require_permission("can_add_items")),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    item = await repo.get_with_location(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if "location_id" in payload.model_fields_set:
        await repo.check_location_exists(payload.location_id)
    if "platform_id" in payload.model_fields_set:
        await repo.check_platform_exists(payload.platform_id)

    if "media_subtype_id" in payload.model_fields_set and payload.media_subtype_id is not None:
        subtype = await repo.resolve_subtype(payload.media_subtype_id)
    else:
        subtype = await repo.resolve_subtype(item.media_subtype_id)

    new_location_id = payload.location_id if "location_id" in payload.model_fields_set else item.location_id
    new_platform_id = payload.platform_id if "platform_id" in payload.model_fields_set else item.platform_id
    _validate_ownership_fields(subtype.supertype, new_location_id, new_platform_id)

    old_url = item.cover_image_url
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    if payload.cover_image_url and payload.cover_image_url != old_url:
        background_tasks.add_task(_fetch_cover_in_background, item.id, payload.cover_image_url)

    await repo.commit()
    item = await repo.reload(item.id)
    return await _build_response(repo, item)


@router.delete("/{item_id}", status_code=204)
async def delete_media(item_id: int, _=Depends(require_permission("can_add_items")), repo: MediaItemRepository = Depends(get_media_item_repository)):
    item = await repo.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    for link in await repo.links_for_item(item_id):
        await repo.delete_link(link)

    delete_cover_files(item.cover_image_path)

    await repo.delete(item)
    await repo.commit()


@router.delete("/{item_id}/link/{other_id}", status_code=204)
async def unlink_item(
    item_id: int,
    other_id: int,
    _=Depends(require_permission("can_add_items")),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    link = await repo.get_link(item_id, other_id)
    if link is None:
        raise HTTPException(status_code=404, detail="These items are not linked")

    await repo.delete_link(link)
    await repo.commit()


@router.post("/{item_id}/cover", response_model=MediaItemResponse)
async def upload_cover(
    item_id: int,
    file: UploadFile = File(...),
    _=Depends(require_permission("can_add_items")),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    item = await repo.get_with_location(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if file.content_type not in ALLOWED_COVER_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPEG, PNG, WebP, GIF or BMP.")

    data = await file.read()
    if len(data) > MAX_COVER_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")

    local_path = await optimise_and_save(data, item_id, "custom")
    if local_path is None:
        raise HTTPException(status_code=400, detail="File is not a valid image")

    item.cover_image_path = local_path
    item.cover_image_url = None
    await repo.commit()
    item = await repo.reload(item.id)
    return await _build_response(repo, item)


@router.delete("/{item_id}/cover", response_model=MediaItemResponse)
async def delete_cover(
    item_id: int,
    _=Depends(require_permission("can_add_items")),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    """Remove a locally-stored cover (uploaded or downloaded), falling back
    to `cover_image_url` (if set) for `cover_url`."""
    item = await repo.get_with_location(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    delete_cover_files(item.cover_image_path)
    item.cover_image_path = None
    await repo.commit()
    item = await repo.reload(item.id)
    return await _build_response(repo, item)


@router.post("/{item_id}/cover/refresh", response_model=MediaItemResponse)
async def refresh_cover(
    item_id: int,
    _=Depends(require_permission("can_add_items")),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    """Re-download and re-optimise an item's cover from its `cover_image_url`."""
    item = await repo.get_with_location(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.cover_image_url:
        raise HTTPException(status_code=400, detail="Item has no cover URL to refresh from")

    local_path = await download_cover(item.cover_image_url, item_id, force=True)
    if local_path is None:
        raise HTTPException(status_code=502, detail="Failed to download cover image")

    item.cover_image_path = local_path
    await repo.commit()
    item = await repo.reload(item.id)
    return await _build_response(repo, item)
