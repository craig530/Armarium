import asyncio
import io
import hashlib
import ipaddress
import socket
import httpx
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

from ..config import settings

MAX_WIDTH = 500
JPEG_QUALITY = 85

# Generous ceiling for cover art — blocks decompression-bomb style images
# (e.g. a 1x1 PNG that decodes to gigapixels) while allowing real artwork.
MAX_IMAGE_PIXELS = 40_000_000  # ~40MP
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def _optimise(data: bytes) -> Optional[bytes]:
    """Resize to MAX_WIDTH and re-encode as optimised progressive JPEG.

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
    if w > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, int(h * MAX_WIDTH / w)), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return out.getvalue()


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
    """Download a cover image, optimise it, and return the local serve path."""
    if not url:
        return None

    if not await _is_safe_url(url):
        return None

    covers_dir = Path(settings.covers_dir)
    covers_dir.mkdir(parents=True, exist_ok=True)

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    filename = f"{item_id}_{url_hash}.jpg"
    filepath = covers_dir / filename

    if filepath.exists():
        return f"/covers/{filename}"

    # Redirects are not followed: a "safe" URL could redirect to an internal
    # address, which would bypass the check above.
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 500:
                optimised = _optimise(resp.content)
                if optimised is not None:
                    filepath.write_bytes(optimised)
                    return f"/covers/{filename}"
        except httpx.HTTPError:
            pass

    return None


async def optimise_and_save(data: bytes, item_id: int, suffix: str = "upload") -> Optional[str]:
    """Optimise raw image bytes and save locally. Returns local serve path, or
    None if the data isn't a valid image."""
    optimised = _optimise(data)
    if optimised is None:
        return None

    covers_dir = Path(settings.covers_dir)
    covers_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{item_id}_{suffix}.jpg"
    filepath = covers_dir / filename
    filepath.write_bytes(optimised)
    return f"/covers/{filename}"
