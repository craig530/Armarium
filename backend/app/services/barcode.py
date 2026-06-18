import logging
import re

logger = logging.getLogger("armarium")

_ISBN_PREFIXES = ("978", "979")


def process_barcode(raw_input: str) -> dict:
    """Normalise and validate a scanned/typed barcode, and prepare the
    per-provider lookup values consumed by the lookup endpoints.

    Handles ISBN-13 book barcodes (including ones fused with an EAN-5 price
    extension), and UPC-A/EAN-13 barcodes for CDs, DVDs and Blu-rays. Returns
    a dict — see `lookups` keys for the exact value each external API
    (MusicBrainz, Discogs, TMDB, Open Library) expects.
    """
    raw_cleaned = re.sub(r"[\s-]", "", raw_input or "")

    result = {
        "media_hint": "unknown",
        "valid": False,
        "error": None,
        "raw_cleaned": raw_cleaned,
        "lookups": {
            "isbn13": None,
            "upc_a": None,
            "ean13": None,
            "ean13_from_upc": None,
            "discogs_raw": None,
            "musicbrainz": None,
            "tmdb_barcode": None,
            "open_library": None,
        },
    }

    if not raw_cleaned.isdigit():
        result["error"] = f"'{raw_cleaned}' is not a valid barcode — expected digits only."
        _log(raw_input, result)
        return result

    length = len(raw_cleaned)

    # Books: ISBN-13 / Bookland EAN-13 (prefix 978 or 979)
    if raw_cleaned.startswith(_ISBN_PREFIXES):
        if length == 13:
            isbn13 = raw_cleaned
        elif length == 18:
            # Scanner captured the EAN-13 fused with its EAN-5 price extension.
            isbn13 = raw_cleaned[:13]
        else:
            result["error"] = (
                f"Invalid book barcode: '{raw_cleaned}' starts with {raw_cleaned[:3]} "
                f"but is {length} digits — expected 13, or 18 with a price extension."
            )
            _log(raw_input, result)
            return result

        result["valid"] = True
        result["media_hint"] = "book"
        result["lookups"]["isbn13"] = isbn13
        result["lookups"]["open_library"] = isbn13
        _log(raw_input, result)
        return result

    # GTIN-14 / ITF-14 (14 digits, e.g. some Nintendo Switch cartridge boxes):
    # strip the leading packaging indicator and retry as EAN-13.
    if length == 14 and raw_cleaned[0] == "0":
        return process_barcode(raw_cleaned[1:])

    # CDs, DVDs and Blu-rays: UPC-A (12 digits) or EAN-13 (13 digits)
    if length == 12:
        upc_a = raw_cleaned
        ean13_from_upc = "0" + upc_a

        result["valid"] = True
        result["media_hint"] = "unknown"
        result["lookups"]["upc_a"] = upc_a
        result["lookups"]["ean13_from_upc"] = ean13_from_upc
        result["lookups"]["musicbrainz"] = ean13_from_upc
        result["lookups"]["discogs_raw"] = upc_a.lstrip("0") or "0"
        result["lookups"]["tmdb_barcode"] = upc_a
        _log(raw_input, result)
        return result

    if length == 13:
        ean13 = raw_cleaned

        result["valid"] = True
        result["media_hint"] = "unknown"
        result["lookups"]["ean13"] = ean13
        result["lookups"]["musicbrainz"] = ean13
        result["lookups"]["discogs_raw"] = ean13.lstrip("0") or "0"
        result["lookups"]["tmdb_barcode"] = ean13
        _log(raw_input, result)
        return result

    result["error"] = (
        f"Unrecognised barcode: '{raw_cleaned}' ({length} digits) doesn't match a known "
        f"book (ISBN-13), UPC-A or EAN-13 format."
    )
    _log(raw_input, result)
    return result


def _log(raw_input: str, result: dict) -> None:
    # Invalid barcodes are logged at WARNING so they're visible with the
    # project's default logging config — useful for diagnosing scanner issues.
    level = logging.INFO if result["valid"] else logging.WARNING
    logger.log(
        level,
        "Barcode processed: raw=%r cleaned=%r media_hint=%s valid=%s error=%s",
        raw_input,
        result["raw_cleaned"],
        result["media_hint"],
        result["valid"],
        result["error"],
    )
