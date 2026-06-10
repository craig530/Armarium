import httpx
import logging
import re
from typing import List, Optional
from ..schemas.media import LookupCandidate, MediaType

logger = logging.getLogger("armarium")

BASE_URL = "https://openlibrary.org"
COVERS_URL = "https://covers.openlibrary.org"
HEADERS = {"User-Agent": "Armarium/1.0 (media-catalogue)"}


async def lookup_by_isbn(isbn: str) -> List[LookupCandidate]:
    clean = isbn.replace("-", "").strip()
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/api/books",
                params={"bibkeys": f"ISBN:{clean}", "format": "json", "jscmd": "data"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("OpenLibrary ISBN lookup failed for %s: %s", clean, e)
            return []

    return [c for c in (_isbn_book_to_candidate(book, clean) for book in data.values()) if c]


async def search_books(query: str, limit: int = 10) -> List[LookupCandidate]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/search.json",
                params={
                    "q": query,
                    "limit": limit,
                    "fields": "key,title,author_name,first_publish_year,isbn,cover_i,publisher,subject",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("OpenLibrary search failed for %r: %s", query, e)
            return []

    return [c for c in (_search_doc_to_candidate(d) for d in data.get("docs", [])) if c][:limit]


def _isbn_book_to_candidate(book: dict, isbn: str) -> Optional[LookupCandidate]:
    title = book.get("title")
    if not title:
        return None

    authors = book.get("authors", [])
    author = ", ".join(a.get("name", "") for a in authors) if authors else None

    publishers = book.get("publishers", [])
    publisher = publishers[0].get("name") if publishers else None

    year = None
    pd = book.get("publish_date", "")
    m = re.search(r"\b(19|20)\d{2}\b", pd)
    if m:
        year = int(m.group())

    covers = book.get("cover", {})
    cover_url = covers.get("large") or covers.get("medium") or covers.get("small")

    subjects = book.get("subjects", [])
    genres = ", ".join(
        (s.get("name", "") if isinstance(s, dict) else s) for s in subjects[:5]
    )

    metadata = {
        "title": title,
        "author": author,
        "publisher": publisher,
        "year": year,
        "isbn": isbn,
        "genres": genres,
        "cover_image_url": cover_url,
        "openlibrary_id": book.get("key"),
        "page_count": book.get("number_of_pages"),
        "description": _first_excerpt(book.get("excerpts", [])),
    }

    return LookupCandidate(
        external_id=isbn,
        source="openlibrary",
        title=title,
        year=year,
        media_type=MediaType.BOOK,
        creator=author,
        cover_url=cover_url,
        metadata=metadata,
    )


def _search_doc_to_candidate(doc: dict) -> Optional[LookupCandidate]:
    title = doc.get("title")
    if not title:
        return None

    authors = doc.get("author_name", [])
    author = ", ".join(authors[:3]) if authors else None
    year = doc.get("first_publish_year")

    cover_id = doc.get("cover_i")
    cover_url = f"{COVERS_URL}/b/id/{cover_id}-L.jpg" if cover_id else None

    isbn_list = doc.get("isbn", [])
    isbn = isbn_list[0] if isbn_list else ""

    publishers = doc.get("publisher", [])
    publisher = publishers[0] if publishers else None

    subjects = doc.get("subject", [])
    genres = ", ".join(subjects[:5]) if subjects else None

    metadata = {
        "title": title,
        "author": author,
        "publisher": publisher,
        "year": year,
        "isbn": isbn,
        "genres": genres,
        "cover_image_url": cover_url,
        "openlibrary_id": doc.get("key"),
    }

    return LookupCandidate(
        external_id=doc.get("key", isbn),
        source="openlibrary",
        title=title,
        year=year,
        media_type=MediaType.BOOK,
        creator=author,
        cover_url=cover_url,
        metadata=metadata,
    )


def _first_excerpt(excerpts: list) -> Optional[str]:
    if excerpts:
        return excerpts[0].get("text")
    return None
