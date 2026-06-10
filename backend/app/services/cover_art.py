import io
import hashlib
import httpx
from pathlib import Path
from typing import Optional

from PIL import Image

from ..config import settings

MAX_WIDTH = 500
JPEG_QUALITY = 85


def _optimise(data: bytes) -> bytes:
    """Resize to MAX_WIDTH and re-encode as optimised progressive JPEG."""
    try:
        img = Image.open(io.BytesIO(data))
        # Flatten transparency
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
    except Exception:
        return data  # return original bytes on any failure


async def download_cover(url: str, item_id: int) -> Optional[str]:
    """Download a cover image, optimise it, and return the local serve path."""
    if not url:
        return None

    covers_dir = Path(settings.covers_dir)
    covers_dir.mkdir(parents=True, exist_ok=True)

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    filename = f"{item_id}_{url_hash}.jpg"
    filepath = covers_dir / filename

    if filepath.exists():
        return f"/covers/{filename}"

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 500:
                optimised = _optimise(resp.content)
                filepath.write_bytes(optimised)
                return f"/covers/{filename}"
        except Exception:
            pass

    return None


async def optimise_and_save(data: bytes, item_id: int, suffix: str = "upload") -> str:
    """Optimise raw image bytes and save locally. Returns local serve path."""
    covers_dir = Path(settings.covers_dir)
    covers_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{item_id}_{suffix}.jpg"
    filepath = covers_dir / filename
    filepath.write_bytes(_optimise(data))
    return f"/covers/{filename}"
