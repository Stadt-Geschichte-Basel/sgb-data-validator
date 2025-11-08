"""Integration tests for Issue #31 - End-to-end transformation workflows."""

from src.transformations import (
    apply_text_transformations,
    transform_item,
    transform_media,
)


def test_complete_item_transformation() -> None:
    """Test complete item transformation with all Issue #31 features."""
    print("\nIntegration Test: Complete item transformation")
    print("=" * 60)

    # Simulate an item with various data quality issues
    item_data = {
        "o:id": 12345,
        "o:title": "&Uuml;ber  d.j.  Basel  ",  # HTML entity, abbreviation, extra spaces
        "dcterms:description": [
            {
                "type": "literal",
                "@value": "Eine lange Ge\u00adschichte\u00a0mit "
                "ver\u00adschie\u00addenen Prob\u00adlemen.\n\n\n\n"
                "M&ouml;chten Sie mehr er\u00adfah\u00adren?",
                # Soft hyphens, NBSP, HTML entities, multiple newlines
                "property_id": 4,
            }
        ],
        "dcterms:subject": [
            {
                "type": "literal",
                "@value": "Basel d.ä. Stadt",  # Abbreviation
                "property_id": 5,
            }
        ],
        "dcterms:references": [
            {
                "type": "literal",
                "@value": "(http://example.com)[Source]",  # Reversed Markdown link
                "property_id": 6,
            }
        ],
        "dcterms:relation": [
            {
                "type": "literal",
                "@value": "m.wikidata.org/wiki/Q78",  # Mobile Wikidata URL
                "property_id": 7,
            }
        ],
        "dcterms:source": [
            {
                "type": "uri",
                "@id": "https://example.com",  # Should not be transformed
                "property_id": 8,
            }
        ],
    }

    # Apply all transformations
    result = transform_item(item_data, apply_all=True)

    # Verify transformations
    assert result["o:title"] == "Über d. J. Basel", (
        f"Title should be normalized, got: {result['o:title']}"
    )

    desc_value = result["dcterms:description"][0]["@value"]
    assert "Ge\u00adschichte" not in desc_value, "Soft hyphens should be removed"
    assert "\u00a0" not in desc_value, "NBSP should be removed"
    assert "&ouml;" not in desc_value, "HTML entities should be converted"
    assert "\n\n\n" not in desc_value, "Multiple newlines should be normalized"
    expected_desc = (
        "Eine lange Geschichte mit verschiedenen Problemen.\n\n"
        "Möchten Sie mehr erfahren?"
    )
    assert desc_value == expected_desc, (
        f"Description mismatch.\nExpected: {repr(expected_desc)}\n"
        f"Got: {repr(desc_value)}"
    )

    subject_value = result["dcterms:subject"][0]["@value"]
    assert subject_value == "Basel d. Ä. Stadt", (
        f"Subject should have normalized abbreviation, got: {subject_value}"
    )

    references_value = result["dcterms:references"][0]["@value"]
    assert references_value == "[Source](http://www.example.com)", (
        f"References should have correct Markdown format and normalized URL, "
        f"got: {references_value}"
    )

    relation_value = result["dcterms:relation"][0]["@value"]
    assert relation_value == "https://www.wikidata.org/wiki/Q78", (
        f"Relation should have canonical Wikidata URL, got: {relation_value}"
    )

    # URI property should be unchanged
    source_value = result["dcterms:source"][0]["@id"]
    assert source_value == "https://example.com", (
        f"URI property should be unchanged, got: {source_value}"
    )

    print("  ✓ Title normalized (HTML entity + abbreviation)")
    print("  ✓ Description cleaned (soft hyphens, NBSP, HTML entities, newlines)")
    print("  ✓ Subject abbreviation normalized")
    print("  ✓ References Markdown link formatted")
    print("  ✓ Relation Wikidata URL normalized")
    print("  ✓ URI property preserved")


def test_complete_media_transformation() -> None:
    """Test complete media transformation with placeholder detection."""
    print("\nIntegration Test: Complete media transformation")
    print("=" * 60)

    # Media with placeholder file
    media_data = {
        "o:id": 98765,
        "o:filename": "image-sgb-fdp-platzhalter-01.jpg",
        "o:title": "Test  Media  D.J.  &amp;  D.&Auml;.",
        "dcterms:title": [
            {
                "type": "literal",
                "@value": "Test  Image  with  spaces",
                "property_id": 1,
            }
        ],
        "dcterms:description": [
            {
                "type": "literal",
                "@value": "See m.wikidata.org/wiki/Q123 for more",
                "property_id": 4,
            }
        ],
    }

    # Check placeholder detection before transformation
    from src.transformations import has_placeholder_media

    assert has_placeholder_media(media_data), "Should detect placeholder media"

    # Apply all transformations
    result = transform_media(media_data, apply_all=True)

    # Verify transformations
    expected_title = "Test Media d. J. & d. Ä."
    assert result["o:title"] == expected_title, (
        f"Title should be fully normalized.\nExpected: {repr(expected_title)}\n"
        f"Got: {repr(result['o:title'])}"
    )

    dcterms_title = result["dcterms:title"][0]["@value"]
    assert dcterms_title == "Test Image with spaces", (
        f"dcterms:title should have normalized spaces, got: {dcterms_title}"
    )

    description = result["dcterms:description"][0]["@value"]
    assert description == "See https://www.wikidata.org/wiki/Q123 for more", (
        f"Description should have canonical Wikidata URL, got: {description}"
    )

    # Filename should be unchanged (this is for detection, not transformation)
    assert result["o:filename"] == media_data["o:filename"], (
        "Filename should not be changed by transformation"
    )

    print("  ✓ Placeholder media detected")
    print("  ✓ Title normalized (spaces, abbreviations, HTML entities)")
    print("  ✓ dcterms:title spaces normalized")
    print("  ✓ Description Wikidata URL normalized")
    print("  ✓ Filename preserved for detection")


def test_real_world_complex_example() -> None:
    """Test with a realistic complex example combining multiple issues."""
    print("\nIntegration Test: Real-world complex example")
    print("=" * 60)

    # Complex text with multiple issues
    text = (
        "Die Stadt Ba\u00adsel (auch: &lt;Basel&gt;) wurde d.j. 1000 "
        "ge\u00adgr&uuml;n\u00addet.\n\n\n\nMehr In\u00adfor\u00adma\u00adtio\u00adnen "
        "fin\u00adden Sie unter m.wikidata.org/wiki/Q78 oder "
        "[hier] http://example.com/info"
    )

    result = apply_text_transformations(text)

    expected = (
        "Die Stadt Basel (auch: <Basel>) wurde d. J. 1000 gegründet.\n\n"
        "Mehr Informationen finden Sie unter https://www.wikidata.org/wiki/Q78 "
        "oder [hier](http://www.example.com/info)"
    )

    assert result == expected, (
        f"Complex transformation failed.\n"
        f"Expected: {repr(expected)}\n"
        f"Got: {repr(result)}"
    )

    print("  ✓ Soft hyphens removed")
    print("  ✓ HTML entities converted (<, >, ü)")
    print("  ✓ Abbreviation normalized (d.j. → d. J.)")
    print("  ✓ Multiple newlines normalized")
    print("  ✓ Wikidata URL normalized")
    print("  ✓ Markdown link formatted")
    print("  ✓ URL normalized (www. added)")


def test_unicode_composed_forms() -> None:
    """Test that Unicode is properly normalized to composed forms."""
    print("\nIntegration Test: Unicode composed forms")
    print("=" * 60)

    # Text with decomposed Unicode characters
    text_decomposed = "Cafe\u0301"  # é as combining character
    text_composed = "Café"  # é as single character

    # Both should normalize to the same composed form
    result_decomposed = apply_text_transformations(text_decomposed)
    result_composed = apply_text_transformations(text_composed)

    assert result_decomposed == result_composed == "Café", (
        f"Unicode normalization failed.\n"
        f"From decomposed: {repr(result_decomposed)}\n"
        f"From composed: {repr(result_composed)}"
    )

    # More complex example with German umlauts
    text = "Mu\u0308nchen u\u0308ber Zu\u0308rich"  # ü as combining diaeresis
    result = apply_text_transformations(text)
    expected = "München über Zürich"  # ü as composed character

    assert result == expected, (
        f"German umlaut normalization failed.\n"
        f"Expected: {repr(expected)}\n"
        f"Got: {repr(result)}"
    )

    print("  ✓ Decomposed é normalized to composed form")
    print("  ✓ Decomposed ü normalized to composed form")
    print("  ✓ All diacritics in NFC form")


if __name__ == "__main__":
    print("Integration tests for Issue #31")
    print("=" * 60)
    print()

    test_complete_item_transformation()
    test_complete_media_transformation()
    test_real_world_complex_example()
    test_unicode_composed_forms()

    print("\n" + "=" * 60)
    print("✓ All integration tests passed!")
    print("\nSummary:")
    print("  - Complete item transformation: ✓")
    print("  - Complete media transformation: ✓")
    print("  - Real-world complex example: ✓")
    print("  - Unicode composed forms: ✓")
