"""Tests for Issue #31 - Comprehensive Data Validation and Normalization Features."""

from sgb_validator.transformations import (
    apply_text_transformations,
    convert_html_entities,
    has_placeholder_media,
    normalize_abbreviations,
    normalize_markdown_links,
    normalize_unicode_nfc,
    normalize_urls,
    normalize_wikidata_url,
)


def test_normalize_unicode_nfc() -> None:
    """Test Unicode NFC normalization."""
    print("\nTest 1: Unicode NFC normalization")
    print("=" * 60)

    test_cases = [
        # (input, expected, description)
        ("café", "café", "Composed form preserved"),
        ("caf\u00e9", "café", "Decomposed form normalized"),
        ("Zürich", "Zürich", "German umlaut preserved"),
        ("München", "München", "Multiple umlauts preserved"),
        ("naïve", "naïve", "Diaeresis preserved"),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_unicode_nfc(input_text)
        assert result == expected, (
            f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        )
        print(f"  ✓ {description}")


def test_convert_html_entities() -> None:
    """Test HTML entity conversion."""
    print("\nTest 2: HTML entity conversion")
    print("=" * 60)

    test_cases = [
        ("&auml;", "ä", "Named entity auml"),
        ("&ouml;", "ö", "Named entity ouml"),
        ("&uuml;", "ü", "Named entity uuml"),
        ("&#252;", "ü", "Numeric entity 252"),
        ("&amp;", "&", "Named entity amp"),
        ("&lt;tag&gt;", "<tag>", "Named entities lt and gt"),
        ("M&uuml;nchen", "München", "Entity in word"),
        ("&Auml;&Ouml;&Uuml;", "ÄÖÜ", "Multiple entities"),
        ("plain text", "plain text", "No entities unchanged"),
    ]

    for input_text, expected, description in test_cases:
        result = convert_html_entities(input_text)
        assert result == expected, (
            f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        )
        print(f"  ✓ {description}")


def test_normalize_markdown_links() -> None:
    """Test Markdown link format normalization."""
    print("\nTest 3: Markdown link format normalization")
    print("=" * 60)

    test_cases = [
        (
            "[label](https://example.com)",
            "[label](https://example.com)",
            "Correct format preserved",
        ),
        (
            "(https://example.com)[label]",
            "[label](https://example.com)",
            "Reversed format (URL)[label] corrected",
        ),
        (
            "(bunterhund Illustration)[https://bunterhund.ch/]",
            "[bunterhund Illustration](https://bunterhund.ch/)",
            "Reversed format (label)[URL] corrected",
        ),
        (
            "[https://example.com](label)",
            "[label](https://example.com)",
            "Swapped [URL](label) corrected",
        ),
        (
            "[https://bunterhund.ch/](bunterhund Illustration)",
            "[bunterhund Illustration](https://bunterhund.ch/)",
            "Swapped [URL](label) with description corrected",
        ),
        (
            "[label] https://example.com",
            "[label](https://example.com)",
            "Missing parentheses added",
        ),
        (
            "Text [link](url) more text",
            "Text [link](url) more text",
            "Inline link preserved",
        ),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_markdown_links(input_text)
        assert result == expected, (
            f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        )
        print(f"  ✓ {description}")


def test_normalize_abbreviations() -> None:
    """Test abbreviation normalization."""
    print("\nTest 4: Abbreviation normalization")
    print("=" * 60)

    test_cases = [
        # d.j. variations
        ("d.j.", "d. J.", "d.j. normalized"),
        ("d. j.", "d. J.", "d. j. normalized"),
        ("D. J.", "d. J.", "D. J. normalized"),
        ("d.J.", "d. J.", "d.J. normalized"),
        ("D.j.", "d. J.", "D.j. normalized"),
        # d.ä. variations
        ("d.ä.", "d. Ä.", "d.ä. normalized"),
        ("d. ä.", "d. Ä.", "d. ä. normalized"),
        ("D. Ä.", "d. Ä.", "D. Ä. normalized"),
        ("d.Ä.", "d. Ä.", "d.Ä. normalized"),
        ("D.ä.", "d. Ä.", "D.ä. normalized"),
        # In context
        ("Text d.j. more", "Text d. J. more", "d.j. in context"),
        ("Text d.ä. more", "Text d. Ä. more", "d.ä. in context"),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_abbreviations(input_text)
        assert result == expected, (
            f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        )
        print(f"  ✓ {description}")


def test_normalize_wikidata_url() -> None:
    """Test Wikidata URL normalization."""
    print("\nTest 5: Wikidata URL normalization")
    print("=" * 60)

    test_cases = [
        (
            "m.wikidata.org/wiki/Q123",
            "https://www.wikidata.org/wiki/Q123",
            "Mobile URL without protocol",
        ),
        (
            "http://m.wikidata.org/wiki/Q456",
            "https://www.wikidata.org/wiki/Q456",
            "Mobile URL with http",
        ),
        (
            "https://m.wikidata.org/wiki/Q789",
            "https://www.wikidata.org/wiki/Q789",
            "Mobile URL with https",
        ),
        (
            "Text m.wikidata.org/wiki/Q999 more",
            "Text https://www.wikidata.org/wiki/Q999 more",
            "Mobile URL in context",
        ),
        (
            "https://www.wikidata.org/wiki/Q111",
            "https://www.wikidata.org/wiki/Q111",
            "Canonical URL unchanged",
        ),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_wikidata_url(input_text)
        assert result == expected, (
            f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        )
        print(f"  ✓ {description}")


def test_normalize_urls() -> None:
    """Test general URL normalization."""
    print("\nTest 6: General URL normalization")
    print("=" * 60)

    test_cases = [
        (
            "https://example.com",
            "https://example.com",
            "Do not add www prefix",
        ),
        (
            "http://example.com",
            "http://example.com",
            "Do not add www prefix to http",
        ),
        (
            "https://www.example.com",
            "https://www.example.com",
            "Preserve existing www",
        ),
        (
            "https://www.example.com/",
            "https://www.example.com",
            "Remove trailing slash",
        ),
        (
            "https://www.example.com/page",
            "https://www.example.com/page",
            "Keep path without trailing slash",
        ),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_urls(input_text)
        assert result == expected, (
            f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        )
        print(f"  ✓ {description}")


def test_apply_text_transformations() -> None:
    """Test comprehensive text transformation."""
    print("\nTest 7: Comprehensive text transformation")
    print("=" * 60)

    test_cases = [
        (
            "&auml;&ouml;&uuml;",
            "äöü",
            "HTML entities converted",
        ),
        (
            "d.j. test",
            "d. J. test",
            "Abbreviation normalized",
        ),
        (
            "m.wikidata.org/wiki/Q123",
            "https://www.wikidata.org/wiki/Q123",
            "Wikidata URL normalized",
        ),
        (
            "[label] https://example.com",
            "[label](https://example.com)",
            "Markdown link formatted without adding www",
        ),
        (
            "&uuml;ber  d.j.  with  spaces",
            "über d. J. with spaces",
            "Multiple transformations combined",
        ),
    ]

    for input_text, expected, description in test_cases:
        result = apply_text_transformations(input_text)
        assert result == expected, (
            f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        )
        print(f"  ✓ {description}")


def test_has_placeholder_media() -> None:
    """Test placeholder media detection."""
    print("\nTest 8: Placeholder media detection")
    print("=" * 60)

    test_cases = [
        (
            {"o:filename": "sgb-fdp-platzhalter.jpg"},
            True,
            "Placeholder file detected",
        ),
        (
            {"o:filename": "image-sgb-fdp-platzhalter-01.jpg"},
            True,
            "Placeholder in middle of filename",
        ),
        (
            {"o:filename": "SGB-FDP-PLATZHALTER.jpg"},
            True,
            "Case insensitive detection",
        ),
        (
            {"o:filename": "regular-image.jpg"},
            False,
            "Regular file not detected",
        ),
        (
            {"o:filename": ""},
            False,
            "Empty filename",
        ),
        (
            {},
            False,
            "Missing filename field",
        ),
    ]

    for media_data, expected, description in test_cases:
        result = has_placeholder_media(media_data)
        assert result == expected, (
            f"{description} failed: expected {expected}, got {result}"
        )
        print(f"  ✓ {description}")
