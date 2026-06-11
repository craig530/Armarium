import io
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

# Custom location icons / platform logos: small raster images, stored as-is
# (no re-encoding) so PNG transparency survives. Validated for type/size only
# — `cover_art.py` already raises Image.MAX_IMAGE_PIXELS globally to guard
# against decompression bombs.
#
# SVG is deliberately NOT accepted here: it's served as-is via StaticFiles
# with Content-Type: image/svg+xml, and a browser navigating to that URL
# directly (rather than via <img>) treats it as a full document and executes
# any embedded <script> — a stored-XSS vector against the same origin that
# holds the auth token in localStorage.
ALLOWED_ASSET_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/bmp": "bmp",
}


async def save_asset(data: bytes, content_type: str, directory: str, filename_stem: str) -> Optional[str]:
    """Validate an uploaded icon/logo image and save it as-is.

    Returns the saved filename (relative to `directory`), or None if the
    data isn't a valid image of an allowed type.
    """
    ext = ALLOWED_ASSET_TYPES.get(content_type)
    if ext is None:
        return None

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except (UnidentifiedImageError, OSError):
        return None

    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{filename_stem}.{ext}"
    (out_dir / filename).write_bytes(data)
    return filename


def remove_asset(directory: str, asset_path: Optional[str]) -> None:
    """Delete a previously saved custom asset, if any."""
    if not asset_path:
        return
    (Path(directory) / Path(asset_path).name).unlink(missing_ok=True)
