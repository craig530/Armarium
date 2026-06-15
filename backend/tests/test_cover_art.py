"""Tests for the external-cover-fetch redirect handling in
`app.services.cover_art` — covers.openlibrary.org redirects to an
archive.org mirror, which can itself add a second redirect for files stored
inside a zipped collection."""
import io
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image

from app.services import cover_art

ORIGIN = "https://covers.openlibrary.org/b/id/14361782-L.jpg"
HOP1 = "https://archive.org/download/l_covers_0014/l_covers_0014_36.zip/0014361782-L.jpg"
HOP2 = "https://ia800505.us.archive.org/view_archive.php?archive=/35/items/l_covers_0014/l_covers_0014_36.zip&file=0014361782-L.jpg"


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (300, 300), (200, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _patched_client(handler):
    transport = httpx.MockTransport(handler)

    class _Client(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    return patch("app.services.cover_art.httpx.AsyncClient", _Client)


def _two_hop_handler(final_response):
    def handler(request):
        url = str(request.url)
        if url == ORIGIN:
            return httpx.Response(302, headers={"location": HOP1})
        if url == HOP1:
            return httpx.Response(302, headers={"location": HOP2})
        if url == HOP2:
            return final_response
        raise AssertionError(f"unexpected request to {url}")
    return handler


async def test_download_cover_follows_two_redirect_hops():
    jpeg = _jpeg_bytes()
    handler = _two_hop_handler(httpx.Response(200, content=jpeg, headers={"content-type": "image/jpeg"}))

    with _patched_client(handler), patch("app.services.cover_art._is_safe_url", new=AsyncMock(return_value=True)):
        result = await cover_art.download_cover(ORIGIN, item_id=12345)

    assert result is not None
    assert result.startswith("/covers/")

    cover_art.delete_cover_files(result)


async def test_fetch_remote_image_follows_two_redirect_hops():
    jpeg = _jpeg_bytes()
    handler = _two_hop_handler(httpx.Response(200, content=jpeg, headers={"content-type": "image/jpeg"}))

    with _patched_client(handler), patch("app.services.cover_art._is_safe_url", new=AsyncMock(return_value=True)):
        result = await cover_art.fetch_remote_image(ORIGIN)

    assert result is not None
    data, content_type = result
    assert data == jpeg
    assert content_type == "image/jpeg"


async def test_download_cover_gives_up_after_max_redirects():
    # One hop beyond MAX_REDIRECTS should exhaust the loop and return None,
    # rather than following an unbounded redirect chain.
    chain = [ORIGIN] + [f"{HOP1}?hop={i}" for i in range(cover_art.MAX_REDIRECTS + 1)]

    def handler(request):
        url = str(request.url)
        idx = chain.index(url)
        return httpx.Response(302, headers={"location": chain[idx + 1]})

    with _patched_client(handler), patch("app.services.cover_art._is_safe_url", new=AsyncMock(return_value=True)):
        result = await cover_art.download_cover(ORIGIN, item_id=12345)

    assert result is None
