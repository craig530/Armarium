import asyncio
import io
import hashlib
import ipaddress
import socket
import httpx
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

from PIL import Image, UnidentifiedImageError

from ..config import settings

MAX_WIDTH = 500
THUMB_WIDTH = 200
JPEG_QUALITY = 85

# Generous ceiling for cover art — blocks decompression-bomb style images
# (e.g. a 1x1 PNG that decodes to gigapixels) while allowing real artwork.
MAX_IMAGE_PIXELS = 40_000_000  # ~40MP
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

PROXY_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_PROXY_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def _optimise(data: bytes, max_width: int = MAX_WIDTH) -> Optional[bytes]:
    """Resize to `max_width` and re-encode as optimised progressive JPEG.

    Returns None if the data isn't a valid, reasonably-sized image.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # force full decode now, so corrupt/oversized data fails here
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None

    if img.width * img.height > MAX_IMAGE_PIXELS:
        return None

    if img.mode in ("RGBA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if w > max_width:
        img = img.resize((max_width, int(h * max_width / w)), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return out.getvalue()


def _item_subdir(item_id: int) -> str:
    """Two-level hashed subdirectory for an item's cover files, so a
    catalogue with tens of thousands of items doesn't end up with tens of
    thousands of files in a single flat `covers/` directory."""
    h = hashlib.md5(str(item_id).encode()).hexdigest()
    return f"{h[:2]}/{h[2:4]}"


def _save_sized(data: bytes, dest_dir: Path, stem: str) -> bool:
    """Write `<stem>.jpg` (medium, MAX_WIDTH) and `<stem>_thumb.jpg`
    (THUMB_WIDTH) for an image. Returns False if `data` isn't a valid image."""
    medium = _optimise(data, MAX_WIDTH)
    if medium is None:
        return False
    thumb = _optimise(data, THUMB_WIDTH) or medium

    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / f"{stem}.jpg").write_bytes(medium)
    (dest_dir / f"{stem}_thumb.jpg").write_bytes(thumb)
    return True


def cover_urls(cover_image_path: Optional[str], cover_image_url: Optional[str]) -> tuple:
    """Return `(cover_url, cover_thumb_url)` for an item.

    `cover_image_path` is the value returned by `download_cover` /
    `optimise_and_save` — already a `/covers/...` URL path. New-style paths
    include a hashed subdirectory (`/covers/ab/cd/<stem>.jpg`) and have a
    `<stem>_thumb.jpg` sibling; older rows are flat (`/covers/<stem>.jpg`)
    with no thumbnail, so the thumb URL just falls back to the full image.
    """
    if not cover_image_path:
        return cover_image_url, cover_image_url

    parts = cover_image_path.split("/")
    if len(parts) == 5:  # ['', 'covers', 'ab', 'cd', '<stem>.jpg']
        stem, _, ext = parts[-1].rpartition(".")
        thumb_url = "/".join(parts[:-1] + [f"{stem}_thumb.{ext}"])
    else:
        thumb_url = cover_image_path

    return cover_image_path, thumb_url


def delete_cover_files(cover_image_path: Optional[str]) -> None:
    """Remove the medium image and (if present) thumbnail for a cover path
    returned by `download_cover` / `optimise_and_save`."""
    if not cover_image_path:
        return

    covers_dir = Path(settings.covers_dir)
    cover_file = covers_dir / cover_image_path.removeprefix("/covers/")
    cover_file.unlink(missing_ok=True)

    thumb_file = cover_file.with_name(f"{cover_file.stem}_thumb{cover_file.suffix}")
    thumb_file.unlink(missing_ok=True)


async def _is_safe_url(url: str) -> bool:
    """Reject non-HTTP(S) URLs and URLs that resolve to internal/private addresses.

    Prevents the server from being used as an SSRF proxy via a user-supplied
    cover_image_url (e.g. cloud metadata endpoints, internal services).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False

    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(parsed.hostname, None)
    except (socket.gaierror, UnicodeError):
        return False

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False

    return True


async def download_cover(url: str, item_id: int) -> Optional[str]:
    """Download a cover image, optimise it (medium + thumbnail), and return
    the local serve path for the medium image."""
    if not url:
        return None

    if not await _is_safe_url(url):
        return None

    covers_dir = Path(settings.covers_dir)
    subdir = _item_subdir(item_id)
    dest_dir = covers_dir / subdir

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    stem = f"{item_id}_{url_hash}"
    rel_url = f"/covers/{subdir}/{stem}.jpg"

    if (dest_dir / f"{stem}.jpg").exists():
        return rel_url

    # Redirects are not followed: a "safe" URL could redirect to an internal
    # address, which would bypass the check above.
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 500:
                if _save_sized(resp.content, dest_dir, stem):
                    return rel_url
        except httpx.HTTPError:
            pass

    return None


async def fetch_remote_image(url: str) -> Optional[tuple]:
    """Fetch an external image for the lookup cover-proxy and return
    `(content_bytes, content_type)`, or None.

    Used to display cover art for search results that haven't been saved
    (and thus haven't gone through `download_cover`) yet, so the browser
    never makes a direct request to a third-party host — some self-hosted
    setups have client-side DNS/network rules that block hosts like
    `image.tmdb.org` even though the server (with its own DNS) can reach them.

    Nothing is written to disk. At most one redirect hop is followed (e.g.
    Cover Art Archive's `front-250` 307s to an archive.org mirror), with the
    redirect target re-validated the same way as the original URL.
    """
    if not await _is_safe_url(url):
        return None

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        for _ in range(2):
            try:
                resp = await client.get(url)
            except httpx.HTTPError:
                return None

            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    return None
                url = urljoin(url, location)
                if not await _is_safe_url(url):
                    return None
                continue

            content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            if (
                resp.status_code == 200
                and content_type in PROXY_CONTENT_TYPES
                and len(resp.content) <= MAX_PROXY_IMAGE_BYTES
            ):
                return resp.content, content_type
            return None

    return None


async def optimise_and_save(data: bytes, item_id: int, suffix: str = "upload") -> Optional[str]:
    """Optimise raw image bytes (medium + thumbnail) and save locally.
    Returns the local serve path for the medium image, or None if the data
    isn't a valid image."""
    covers_dir = Path(settings.covers_dir)
    subdir = _item_subdir(item_id)
    dest_dir = covers_dir / subdir
    stem = f"{item_id}_{suffix}"

    if not _save_sized(data, dest_dir, stem):
        return None

    return f"/covers/{subdir}/{stem}.jpg"
