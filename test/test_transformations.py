"""Tests for data transformation utilities."""

import sys

from src.transformations import (
    normalize_whitespace,
    transform_item,
    transform_media,
    transform_property_value,
)


def test_normalize_whitespace_basic() -> bool:
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

    all_passed = True
    for input_text, expected, description in test_cases:
        result = normalize_whitespace(input_text)
        if result == expected:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description}")
            print(f"    Expected: {repr(expected)}")
            print(f"    Got: {repr(result)}")
            all_passed = False

    return all_passed


def test_normalize_whitespace_unicode() -> bool:
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

    all_passed = True
    for input_text, expected, description in test_cases:
        result = normalize_whitespace(input_text)
        if result == expected:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description}")
            print(f"    Input: {repr(input_text)}")
            print(f"    Expected: {repr(expected)}")
            print(f"    Got: {repr(result)}")
            all_passed = False

    return all_passed


def test_normalize_whitespace_multiline() -> bool:
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

    all_passed = True
    for input_text, expected, description in test_cases:
        result = normalize_whitespace(input_text)
        if result == expected:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description}")
            print(f"    Input: {repr(input_text)}")
            print(f"    Expected: {repr(expected)}")
            print(f"    Got: {repr(result)}")
            all_passed = False

    return all_passed


def test_transform_property_value() -> bool:
    """Test transformation of Omeka property values."""
    print("\nTest 4: Property value transformation")
    print("=" * 60)

    all_passed = True

    # Test literal property with whitespace issues
    literal_prop = {
        "type": "literal",
        "@value": "text  with  double\u00a0spaces",
        "property_id": 1,
    }
    result = transform_property_value(literal_prop)
    expected_value = "text with double spaces"
    if result.get("@value") == expected_value and result.get("type") == "literal":
        print("  ✓ Literal property value normalized")
    else:
        print("  ✗ Literal property value not normalized correctly")
        print(f"    Expected: {expected_value}")
        print(f"    Got: {result.get('@value')}")
        all_passed = False

    # Test URI property (should not be transformed)
    uri_prop = {
        "type": "uri",
        "@id": "http://example.com/test",
        "property_id": 2,
    }
    result = transform_property_value(uri_prop)
    if result == uri_prop:
        print("  ✓ URI property unchanged")
    else:
        print("  ✗ URI property was modified")
        all_passed = False

    # Test property without @value
    empty_prop = {"type": "literal", "property_id": 3}
    result = transform_property_value(empty_prop)
    if result == empty_prop:
        print("  ✓ Property without @value unchanged")
    else:
        print("  ✗ Property without @value was modified")
        all_passed = False

    return all_passed


def test_transform_item() -> bool:
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

    all_passed = True

    # Check title was normalized
    expected_title = "Test Item with spaces"
    if result.get("o:title") == expected_title:
        print("  ✓ Item title normalized")
    else:
        print("  ✗ Item title not normalized correctly")
        print(f"    Expected: {expected_title}")
        print(f"    Got: {result.get('o:title')}")
        all_passed = False

    # Check description was normalized
    desc_value = result.get("dcterms:description", [{}])[0].get("@value")
    expected_desc = "Description with doublespaces and softhyphen"
    if desc_value == expected_desc:
        print("  ✓ Description normalized")
    else:
        print("  ✗ Description not normalized correctly")
        print(f"    Expected: {expected_desc}")
        print(f"    Got: {desc_value}")
        all_passed = False

    # Check URI property was not modified
    creator_uri = result.get("dcterms:creator", [{}])[0].get("@id")
    if creator_uri == "http://example.com/creator":
        print("  ✓ URI property preserved")
    else:
        print("  ✗ URI property was modified")
        all_passed = False

    # Check o:id was preserved
    if result.get("o:id") == 12385:
        print("  ✓ Item ID preserved")
    else:
        print("  ✗ Item ID was modified")
        all_passed = False

    return all_passed


def test_transform_media() -> bool:
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

    all_passed = True

    # Check title was normalized
    expected_title = "Media withformatting"
    if result.get("o:title") == expected_title:
        print("  ✓ Media title normalized")
    else:
        print("  ✗ Media title not normalized correctly")
        print(f"    Expected: {expected_title}")
        print(f"    Got: {result.get('o:title')}")
        all_passed = False

    # Check extent was normalized
    extent_value = result.get("dcterms:extent", [{}])[0].get("@value")
    expected_extent = "sizewithdirection"
    if extent_value == expected_extent:
        print("  ✓ Extent normalized")
    else:
        print("  ✗ Extent not normalized correctly")
        print(f"    Expected: {expected_extent}")
        print(f"    Got: {extent_value}")
        all_passed = False

    return all_passed


def test_real_world_examples() -> bool:
    """Test with real-world examples from Issue #28."""
    print("\nTest 7: Real-world examples from Issue #28")
    print("=" * 60)

    all_passed = True

    # Example from abb93285 - double spaces and soft hyphen
    text1 = "eine  lange Ge\u00adschichte  mit doppelten Leerzeichen"
    result1 = normalize_whitespace(text1)
    expected1 = "eine lange Geschichte mit doppelten Leerzeichen"
    if result1 == expected1:
        print("  ✓ abb93285 description cleaned")
    else:
        print("  ✗ abb93285 description not cleaned correctly")
        print(f"    Input: {repr(text1)}")
        print(f"    Expected: {repr(expected1)}")
        print(f"    Got: {repr(result1)}")
        all_passed = False

    # Example with U+202C and U+202A (from m37979 extent field)
    text2 = "text\u202awith\u202cdirectional formatting"
    result2 = normalize_whitespace(text2)
    expected2 = "textwithdirectional formatting"
    if result2 == expected2:
        print("  ✓ m37979 extent field cleaned")
    else:
        print("  ✗ m37979 extent field not cleaned correctly")
        print(f"    Input: {repr(text2)}")
        print(f"    Expected: {repr(expected2)}")
        print(f"    Got: {repr(result2)}")
        all_passed = False

    # Example with multiple line breaks
    text3 = "text\n\n\n\nwith\n\n\ntoo many breaks"
    result3 = normalize_whitespace(text3)
    expected3 = "text\n\nwith\n\ntoo many breaks"
    if result3 == expected3:
        print("  ✓ Multiple line breaks normalized")
    else:
        print("  ✗ Multiple line breaks not normalized correctly")
        print(f"    Input: {repr(text3)}")
        print(f"    Expected: {repr(expected3)}")
        print(f"    Got: {repr(result3)}")
        all_passed = False

    return all_passed


if __name__ == "__main__":
    print("Testing data transformation utilities")
    print("=" * 60)

    all_passed = True

    all_passed &= test_normalize_whitespace_basic()
    all_passed &= test_normalize_whitespace_unicode()
    all_passed &= test_normalize_whitespace_multiline()
    all_passed &= test_transform_property_value()
    all_passed &= test_transform_item()
    all_passed &= test_transform_media()
    all_passed &= test_real_world_examples()

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All transformation tests passed!")
        sys.exit(0)
    else:
        print("✗ Some transformation tests failed")
        sys.exit(1)
