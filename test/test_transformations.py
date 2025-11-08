"""Tests for data transformation utilities."""


from src.transformations import (
    normalize_whitespace,
    transform_item,
    transform_media,
    transform_property_value,
)


def test_normalize_whitespace_basic() -> None:
    """Test basic whitespace normalization."""
    print("\nTest 1: Basic whitespace normalization")
    print("=" * 60)

    test_cases = [
        # (input, expected, description)
        ("normal text", "normal text", "Plain text unchanged"),
        ("double  spaces", "double spaces", "Double spaces normalized"),
        ("  leading spaces", "leading spaces", "Leading spaces removed"),
        ("trailing spaces  ", "trailing spaces", "Trailing spaces removed"),
        ("text\twith\ttabs", "text with tabs", "Tabs converted to spaces"),
        ("multiple   \t  spaces", "multiple spaces", "Mixed spaces normalized"),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_whitespace(input_text)
        assert result == expected, f"{description} failed: expected {repr(expected)}, got {repr(result)}"
        print(f"  ✓ {description}")


def test_normalize_whitespace_unicode() -> None:
    """Test Unicode whitespace normalization (Issue #28)."""
    print("\nTest 2: Unicode whitespace normalization")
    print("=" * 60)

    test_cases = [
        # Non-breaking spaces
        (
            "non\u00a0breaking\u00a0space",
            "non breaking space",
            "Non-breaking space (NBSP)",
        ),
        ("narrow\u202fno-break", "narrow no-break", "Narrow no-break space"),
        # Soft hyphen (should be removed entirely)
        (
            "be\u00adding\u00adter Trenn\u00adstrich",
            "bedingter Trennstrich",
            "Soft hyphen removed",
        ),
        # Zero-width characters
        ("zero\u200bwidth\u200cspace", "zerowidthspace", "Zero-width spaces removed"),
        ("\ufeffBOM at start", "BOM at start", "Zero-width no-break space (BOM)"),
        # Directional formatting (U+202C and U+202A from issue #28)
        (
            "text\u202awith\u202cformatting",
            "textwithformatting",
            "Directional formatting removed",
        ),
        # Line separators
        ("line\u2028separator", "line\nseparator", "Line separator to newline"),
        ("para\u2029graph", "para\ngraph", "Paragraph separator to newline"),
        # Various Unicode spaces
        ("em\u2003space", "em space", "Em space normalized"),
        ("en\u2002space", "en space", "En space normalized"),
        ("thin\u2009space", "thin space", "Thin space normalized"),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_whitespace(input_text)
        assert result == expected, f"{description} failed: input {repr(input_text)}, expected {repr(expected)}, got {repr(result)}"
        print(f"  ✓ {description}")


def test_normalize_whitespace_multiline() -> None:
    """Test multiline text normalization."""
    print("\nTest 3: Multiline text normalization")
    print("=" * 60)

    test_cases = [
        # Single newlines preserved
        ("line one\nline two", "line one\nline two", "Single newlines preserved"),
        # Double newlines preserved (paragraph breaks)
        ("para one\n\npara two", "para one\n\npara two", "Double newlines preserved"),
        # Triple+ newlines normalized to double
        (
            "too\n\n\nmany\n\n\n\nlines",
            "too\n\nmany\n\nlines",
            "Multiple newlines normalized",
        ),
        # Trailing spaces on lines removed
        (
            "line one  \nline two  ",
            "line one\nline two",
            "Trailing spaces per line removed",
        ),
        # Complex example with various issues
        (
            "lange Ge\u00adschichte  \n\n\n  with  double  spaces",
            "lange Geschichte\n\n with double spaces",
            "Complex multiline text",
        ),
    ]

    for input_text, expected, description in test_cases:
        result = normalize_whitespace(input_text)
        assert result == expected, f"{description} failed: input {repr(input_text)}, expected {repr(expected)}, got {repr(result)}"
        print(f"  ✓ {description}")


def test_transform_property_value() -> None:
    """Test transformation of Omeka property values."""
    print("\nTest 4: Property value transformation")
    print("=" * 60)

    # Test literal property with whitespace issues
    literal_prop = {
        "type": "literal",
        "@value": "text  with  double\u00a0spaces",
        "property_id": 1,
    }
    result = transform_property_value(literal_prop)
    expected_value = "text with double spaces"
    assert result.get("@value") == expected_value, f"Literal value normalization failed: expected {expected_value}, got {result.get('@value')}"
    assert result.get("type") == "literal", "Type should remain literal"
    print("  ✓ Literal property value normalized")

    # Test URI property (should not be transformed)
    uri_prop = {
        "type": "uri",
        "@id": "http://example.com/test",
        "property_id": 2,
    }
    result = transform_property_value(uri_prop)
    assert result == uri_prop, "URI property should not be modified"
    print("  ✓ URI property unchanged")

    # Test property without @value
    empty_prop = {"type": "literal", "property_id": 3}
    result = transform_property_value(empty_prop)
    assert result == empty_prop, "Property without @value should not be modified"
    print("  ✓ Property without @value unchanged")


def test_transform_item() -> None:
    """Test transformation of complete item data."""
    print("\nTest 5: Complete item transformation")
    print("=" * 60)

    item_data = {
        "o:id": 12385,
        "o:title": "Test  Item  with\u00a0spaces",
        "dcterms:description": [
            {
                "type": "literal",
                "@value": "Description  with  double\u00adspaces and soft\u00adhyphen",
                "property_id": 4,
            }
        ],
        "dcterms:creator": [
            {
                "type": "uri",
                "@id": "http://example.com/creator",
                "property_id": 5,
            }
        ],
    }

    result = transform_item(item_data)

    # Check title was normalized
    expected_title = "Test Item with spaces"
    assert result.get("o:title") == expected_title, f"Title normalization failed: expected {expected_title}, got {result.get('o:title')}"
    print("  ✓ Item title normalized")

    # Check description was normalized
    desc_value = result.get("dcterms:description", [{}])[0].get("@value")
    expected_desc = "Description with doublespaces and softhyphen"
    assert desc_value == expected_desc, f"Description normalization failed: expected {expected_desc}, got {desc_value}"
    print("  ✓ Description normalized")

    # Check URI property was not modified
    creator_uri = result.get("dcterms:creator", [{}])[0].get("@id")
    assert creator_uri == "http://example.com/creator", "URI property should be preserved"
    print("  ✓ URI property preserved")

    # Check o:id was preserved
    assert result.get("o:id") == 12385, "Item ID should be preserved"
    print("  ✓ Item ID preserved")


def test_transform_media() -> None:
    """Test transformation of media data."""
    print("\nTest 6: Media transformation")
    print("=" * 60)

    media_data = {
        "o:id": 37979,
        "o:title": "Media  with\u202cformatting",
        "dcterms:extent": [
            {
                "type": "literal",
                "@value": "size\u202awith\u202cdirection",
                "property_id": 10,
            }
        ],
    }

    result = transform_media(media_data)

    # Check title was normalized
    expected_title = "Media withformatting"
    assert result.get("o:title") == expected_title, f"Media title normalization failed: expected {expected_title}, got {result.get('o:title')}"
    print("  ✓ Media title normalized")

    # Check extent was normalized
    extent_value = result.get("dcterms:extent", [{}])[0].get("@value")
    expected_extent = "sizewithdirection"
    assert extent_value == expected_extent, f"Extent normalization failed: expected {expected_extent}, got {extent_value}"
    print("  ✓ Extent normalized")


def test_real_world_examples() -> None:
    """Test with real-world examples from Issue #28."""
    print("\nTest 7: Real-world examples from Issue #28")
    print("=" * 60)
    # Example from abb93285 - double spaces and soft hyphen
    text1 = "eine  lange Ge\u00adschichte  mit doppelten Leerzeichen"
    result1 = normalize_whitespace(text1)
    expected1 = "eine lange Geschichte mit doppelten Leerzeichen"
    assert result1 == expected1, f"abb93285 description failed: input {repr(text1)}, expected {repr(expected1)}, got {repr(result1)}"
    print("  ✓ abb93285 description cleaned")

    # Example with U+202C and U+202A (from m37979 extent field)
    text2 = "text\u202awith\u202cdirectional formatting"
    result2 = normalize_whitespace(text2)
    expected2 = "textwithdirectional formatting"
    assert result2 == expected2, f"m37979 extent field failed: input {repr(text2)}, expected {repr(expected2)}, got {repr(result2)}"
    print("  ✓ m37979 extent field cleaned")

    # Example with multiple line breaks
    text3 = "text\n\n\n\nwith\n\n\ntoo many breaks"
    result3 = normalize_whitespace(text3)
    expected3 = "text\n\nwith\n\ntoo many breaks"
    assert result3 == expected3, f"Multiple line breaks failed: input {repr(text3)}, expected {repr(expected3)}, got {repr(result3)}"
    print("  ✓ Multiple line breaks normalized")


if __name__ == "__main__":
    print("Testing data transformation utilities")
    print("=" * 60)

    test_normalize_whitespace_basic()
    test_normalize_whitespace_unicode()
    test_normalize_whitespace_multiline()
    test_transform_property_value()
    test_transform_item()
    test_transform_media()
    test_real_world_examples()

    print("\n" + "=" * 60)
    print("✓ All transformation tests passed!")
