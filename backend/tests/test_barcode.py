"""Unit tests for the barcode normalisation/validation pipeline."""
from app.services.barcode import process_barcode


def test_valid_isbn13_book_barcode():
    result = process_barcode("9780134685991")

    assert result["valid"] is True
    assert result["error"] is None
    assert result["media_hint"] == "book"
    assert result["raw_cleaned"] == "9780134685991"
    assert result["lookups"]["isbn13"] == "9780134685991"
    assert result["lookups"]["open_library"] == "9780134685991"
    # Not a CD/DVD/Blu-ray, so the non-book lookups stay empty
    assert result["lookups"]["upc_a"] is None
    assert result["lookups"]["ean13"] is None
    assert result["lookups"]["musicbrainz"] is None
    assert result["lookups"]["discogs_raw"] is None
    assert result["lookups"]["tmdb_barcode"] is None


def test_isbn13_fused_with_ean5_price_extension():
    # 13-digit ISBN ("9780134685991") + 5-digit price extension ("12345")
    result = process_barcode("978013468599112345")

    assert result["valid"] is True
    assert result["error"] is None
    assert result["media_hint"] == "book"
    assert result["raw_cleaned"] == "978013468599112345"
    assert result["lookups"]["isbn13"] == "9780134685991"
    assert result["lookups"]["open_library"] == "9780134685991"


def test_ean5_price_extension_only_is_rejected():
    result = process_barcode("51995")

    assert result["valid"] is False
    assert result["error"] is not None
    assert "barcode" in result["error"].lower()
    assert all(v is None for v in result["lookups"].values())


def test_valid_upc_a_cd_barcode():
    result = process_barcode("075678563598")

    assert result["valid"] is True
    assert result["error"] is None
    assert result["media_hint"] == "unknown"
    assert result["lookups"]["upc_a"] == "075678563598"
    assert result["lookups"]["ean13_from_upc"] == "0075678563598"
    assert result["lookups"]["musicbrainz"] == "0075678563598"
    assert result["lookups"]["discogs_raw"] == "75678563598"
    assert result["lookups"]["tmdb_barcode"] == "075678563598"
    assert result["lookups"]["isbn13"] is None
    assert result["lookups"]["open_library"] is None


def test_valid_ean13_cd_barcode():
    result = process_barcode("5099750442227")

    assert result["valid"] is True
    assert result["error"] is None
    assert result["media_hint"] == "unknown"
    assert result["lookups"]["ean13"] == "5099750442227"
    assert result["lookups"]["musicbrainz"] == "5099750442227"
    assert result["lookups"]["discogs_raw"] == "5099750442227"
    assert result["lookups"]["tmdb_barcode"] == "5099750442227"
    assert result["lookups"]["upc_a"] is None
    assert result["lookups"]["ean13_from_upc"] is None


def test_ean13_not_starting_with_isbn_prefix_has_no_book_lookup():
    # 13-digit EAN-13 (e.g. a French CD barcode) that doesn't start with
    # 978/979 — valid as a generic product barcode, but must never produce
    # an ISBN/Open Library lookup value.
    result = process_barcode("3916681812733")

    assert result["valid"] is True
    assert result["media_hint"] == "unknown"
    assert result["lookups"]["ean13"] == "3916681812733"
    assert result["lookups"]["isbn13"] is None
    assert result["lookups"]["open_library"] is None


def test_upc_a_with_leading_zero_already_present():
    result = process_barcode("012345678905")

    assert result["valid"] is True
    assert result["media_hint"] == "unknown"
    # Leading zero on the UPC-A form is preserved...
    assert result["lookups"]["upc_a"] == "012345678905"
    # ...and a second zero is prepended for the GTIN-13/EAN-13 form
    assert result["lookups"]["ean13_from_upc"] == "0012345678905"
    # ...but Discogs gets the leading zeros stripped, per its literal-text matching
    assert result["lookups"]["discogs_raw"] == "12345678905"


def test_whitespace_and_hyphens_are_stripped():
    result = process_barcode("978-0-13-468599-1")

    assert result["valid"] is True
    assert result["raw_cleaned"] == "9780134685991"
    assert result["lookups"]["isbn13"] == "9780134685991"

    result2 = process_barcode("  075 6785-6359-8 ")
    assert result2["valid"] is True
    assert result2["raw_cleaned"] == "075678563598"
    assert result2["lookups"]["upc_a"] == "075678563598"


def test_completely_invalid_string_is_rejected_cleanly():
    result = process_barcode("not-a-barcode")

    assert result["valid"] is False
    assert result["media_hint"] == "unknown"
    assert result["error"] is not None
    assert result["raw_cleaned"] == "notabarcode"
    assert all(v is None for v in result["lookups"].values())
