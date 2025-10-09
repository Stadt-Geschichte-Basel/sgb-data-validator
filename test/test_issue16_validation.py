"""Test validation rules from issue #16"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validate import OmekaValidator


def create_minimal_item(item_id: int) -> dict:
    """Create a minimal valid item structure"""
    return {
        "@context": "https://omeka.unibe.ch/api-context",
        "@id": f"https://omeka.unibe.ch/api/items/{item_id}",
        "@type": "o:Item",
        "o:id": item_id,
        "o:is_public": True,
        "o:owner": {"@id": "https://omeka.unibe.ch/api/users/1", "o:id": 1},
        "o:resource_class": None,
        "o:resource_template": None,
        "o:thumbnail": None,
        "o:title": "Test Item",
        "thumbnail_display_urls": {
            "large": "https://example.com/large.jpg",
            "medium": "https://example.com/medium.jpg",
            "small": "https://example.com/small.jpg",
        },
        "o:created": {
            "@value": "2024-01-01T00:00:00+00:00",
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
        },
        "o:modified": {
            "@value": "2024-01-01T00:00:00+00:00",
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
        },
        "o:media": [{"@id": "https://omeka.unibe.ch/api/media/1", "o:id": 1}],
        "o:item_set": [],
        "o:site": [],
        "dcterms:identifier": [
            {
                "type": "literal",
                "property_id": 10,
                "property_label": "Identifier",
                "is_public": True,
                "@value": "test123",
            }
        ],
        "dcterms:title": [
            {
                "type": "literal",
                "property_id": 1,
                "property_label": "Title",
                "is_public": True,
                "@value": "Test Item",
            }
        ],
        "dcterms:description": [
            {
                "type": "literal",
                "property_id": 4,
                "property_label": "Description",
                "is_public": True,
                "@value": "Test description",
            }
        ],
        "dcterms:temporal": [
            {
                "type": "customvocab:14",
                "property_id": 41,
                "property_label": "Temporal Coverage",
                "is_public": True,
                "@value": "Frühe Neuzeit",
                "@language": "de",
            }
        ],
        "dcterms:language": [
            {
                "type": "valuesuggest:lc:iso6391",
                "property_id": 12,
                "property_label": "Language",
                "is_public": True,
                "@value": "de",
            }
        ],
        "dcterms:isPartOf": [
            {
                "type": "literal",
                "property_id": 33,
                "property_label": "Is Part Of",
                "is_public": True,
                "@value": "Test Collection",
            }
        ],
    }


def create_minimal_media(media_id: int) -> dict:
    """Create a minimal valid media structure"""
    return {
        "@context": "https://omeka.unibe.ch/api-context",
        "@id": f"https://omeka.unibe.ch/api/media/{media_id}",
        "@type": "o:Media",
        "o:id": media_id,
        "o:is_public": True,
        "o:owner": {"@id": "https://omeka.unibe.ch/api/users/1", "o:id": 1},
        "o:resource_class": None,
        "o:resource_template": {
            "@id": "https://omeka.unibe.ch/api/resource_templates/1",
            "o:id": 1,
        },
        "o:thumbnail": None,
        "o:title": "Test Media",
        "thumbnail_display_urls": {
            "large": "https://example.com/large.jpg",
            "medium": "https://example.com/medium.jpg",
            "small": "https://example.com/small.jpg",
        },
        "o:created": {
            "@value": "2024-01-01T00:00:00+00:00",
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
        },
        "o:modified": {
            "@value": "2024-01-01T00:00:00+00:00",
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
        },
        "o:ingester": "upload",
        "o:renderer": "file",
        "o:item": {"@id": "https://omeka.unibe.ch/api/items/1", "o:id": 1},
        "o:source": "test.jpg",
        "o:media_type": "image/jpeg",
        "o:sha256": "abc123",
        "o:size": 1000,
        "o:filename": "test.jpg",
        "o:lang": None,
        "o:alt_text": "",
        "o:original_url": "https://example.com/test.jpg",
        "o:thumbnail_urls": {
            "large": "https://example.com/large.jpg",
            "medium": "https://example.com/medium.jpg",
            "small": "https://example.com/small.jpg",
        },
        "data": [],
        "dcterms:identifier": [
            {
                "type": "literal",
                "property_id": 10,
                "property_label": "Identifier",
                "is_public": True,
                "@value": "test123",
            }
        ],
        "dcterms:title": [
            {
                "type": "literal",
                "property_id": 1,
                "property_label": "Title",
                "is_public": True,
                "@value": "Test Media",
            }
        ],
        "dcterms:description": [
            {
                "type": "literal",
                "property_id": 4,
                "property_label": "Description",
                "is_public": True,
                "@value": "Test description",
            }
        ],
        "dcterms:rights": [
            {
                "type": "literal",
                "property_id": 15,
                "property_label": "Rights",
                "is_public": True,
                "@value": "Test rights",
            }
        ],
        "dcterms:license": [
            {
                "type": "customvocab:16",
                "property_id": 49,
                "property_label": "License",
                "is_public": True,
                "@value": "https://creativecommons.org/publicdomain/mark/1.0/",
                "@language": "en",
            }
        ],
        "dcterms:creator": [
            {
                "type": "literal",
                "property_id": 2,
                "property_label": "Creator",
                "is_public": True,
                "@value": "Test Creator",
            }
        ],
        "dcterms:publisher": [
            {
                "type": "literal",
                "property_id": 5,
                "property_label": "Publisher",
                "is_public": True,
                "@value": "Test Publisher",
            }
        ],
        "dcterms:temporal": [
            {
                "type": "customvocab:14",
                "property_id": 41,
                "property_label": "Temporal Coverage",
                "is_public": True,
                "@value": "Frühe Neuzeit",
                "@language": "de",
            }
        ],
        "dcterms:type": [
            {
                "type": "valuesuggestall:dc:types",
                "property_id": 8,
                "property_label": "Type",
                "is_public": True,
                "@id": "http://purl.org/dc/dcmitype/Image",
                "o:label": "Image",
            }
        ],
        "dcterms:format": [
            {
                "type": "customvocab:15",
                "property_id": 9,
                "property_label": "Format",
                "is_public": True,
                "@value": "image/jpeg",
                "@language": "en",
            }
        ],
        "dcterms:extent": [
            {
                "type": "literal",
                "property_id": 25,
                "property_label": "Extent",
                "is_public": True,
                "@value": "1920x1080",
            }
        ],
        "dcterms:source": [
            {
                "type": "uri",
                "property_id": 11,
                "property_label": "Source",
                "is_public": True,
                "@id": "https://example.com/source",
                "o:label": "Test Source",
            }
        ],
        "dcterms:language": [
            {
                "type": "valuesuggest:lc:iso6391",
                "property_id": 12,
                "property_label": "Language",
                "is_public": True,
                "@value": "de",
            }
        ],
    }


def test_item_errors() -> None:
    """Test item validation errors"""
    print("Testing Item errors (issue #16)...")

    # Test missing o:title
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(1)
    item["o:title"] = ""
    validator.validate_item(item)

    # Should have error for empty title (from pydantic) but not from our custom check
    # because pydantic validation fails first
    assert len(validator.errors) > 0
    print("  ✓ Empty o:title generates error")

    # Test missing dcterms:identifier
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(2)
    del item["dcterms:identifier"]
    validator.validate_item(item)
    assert any(
        "dcterms:identifier" in str(e) and "required" in str(e).lower()
        for e in validator.errors
    )
    print("  ✓ Missing dcterms:identifier generates error")

    # Test missing dcterms:description
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(3)
    del item["dcterms:description"]
    validator.validate_item(item)
    assert any(
        "dcterms:description" in str(e) and "required" in str(e).lower()
        for e in validator.errors
    )
    print("  ✓ Missing dcterms:description generates error")

    # Test missing dcterms:temporal
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(4)
    del item["dcterms:temporal"]
    validator.validate_item(item)
    assert any(
        "dcterms:temporal" in str(e) and "required" in str(e).lower()
        for e in validator.errors
    )
    print("  ✓ Missing dcterms:temporal generates error")


def test_item_warnings() -> None:
    """Test item validation warnings"""
    print("\nTesting Item warnings (issue #16)...")

    # Test missing thumbnails and media
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(5)
    item["thumbnail_display_urls"] = None
    item["o:media"] = []
    validator.validate_item(item)
    assert any(
        "thumbnail" in str(w).lower() and "media" in str(w).lower()
        for w in validator.warnings
    )
    print("  ✓ Missing thumbnails and media generates warning")

    # Test missing dcterms:language
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(6)
    del item["dcterms:language"]
    validator.validate_item(item)
    assert any("dcterms:language" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:language generates warning")

    # Test missing dcterms:isPartOf
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(7)
    del item["dcterms:isPartOf"]
    validator.validate_item(item)
    assert any("dcterms:isPartOf" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:isPartOf generates warning")


def test_media_errors() -> None:
    """Test media validation errors"""
    print("\nTesting Media errors (issue #16)...")

    # Test missing dcterms:identifier
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(1)
    del media["dcterms:identifier"]
    validator.validate_media(media)
    assert any(
        "dcterms:identifier" in str(e) and "required" in str(e).lower()
        for e in validator.errors
    )
    print("  ✓ Missing dcterms:identifier generates error")

    # Test missing dcterms:description
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(2)
    del media["dcterms:description"]
    validator.validate_media(media)
    assert any(
        "dcterms:description" in str(e) and "required" in str(e).lower()
        for e in validator.errors
    )
    print("  ✓ Missing dcterms:description generates error")

    # Test missing dcterms:rights
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(3)
    del media["dcterms:rights"]
    validator.validate_media(media)
    assert any(
        "dcterms:rights" in str(e) and "required" in str(e).lower()
        for e in validator.errors
    )
    print("  ✓ Missing dcterms:rights generates error")

    # Test missing dcterms:license
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(4)
    del media["dcterms:license"]
    validator.validate_media(media)
    assert any(
        "dcterms:license" in str(e) and "required" in str(e).lower()
        for e in validator.errors
    )
    print("  ✓ Missing dcterms:license generates error")


def test_media_warnings() -> None:
    """Test media validation warnings"""
    print("\nTesting Media warnings (issue #16)...")

    # Test missing o:resource_template
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(5)
    media["o:resource_template"] = None
    validator.validate_media(media)
    assert any("resource_template" in str(w).lower() for w in validator.warnings)
    print("  ✓ Missing o:resource_template generates warning")

    # Test missing thumbnails
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(6)
    media["thumbnail_display_urls"] = None
    validator.validate_media(media)
    assert any("thumbnail" in str(w).lower() for w in validator.warnings)
    print("  ✓ Missing thumbnails generates warning")

    # Test missing dcterms:creator
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(7)
    del media["dcterms:creator"]
    validator.validate_media(media)
    assert any("dcterms:creator" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:creator generates warning")

    # Test missing dcterms:publisher
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(8)
    del media["dcterms:publisher"]
    validator.validate_media(media)
    assert any("dcterms:publisher" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:publisher generates warning")

    # Test missing dcterms:temporal
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(9)
    del media["dcterms:temporal"]
    validator.validate_media(media)
    assert any("dcterms:temporal" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:temporal generates warning")

    # Test missing dcterms:type
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(10)
    del media["dcterms:type"]
    validator.validate_media(media)
    assert any("dcterms:type" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:type generates warning")

    # Test missing dcterms:format
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(11)
    del media["dcterms:format"]
    validator.validate_media(media)
    assert any("dcterms:format" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:format generates warning")

    # Test missing dcterms:extent
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(12)
    del media["dcterms:extent"]
    validator.validate_media(media)
    assert any("dcterms:extent" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:extent generates warning")

    # Test missing dcterms:source
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(13)
    del media["dcterms:source"]
    validator.validate_media(media)
    assert any("dcterms:source" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:source generates warning")

    # Test missing dcterms:language
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(14)
    del media["dcterms:language"]
    validator.validate_media(media)
    assert any("dcterms:language" in str(w) for w in validator.warnings)
    print("  ✓ Missing dcterms:language generates warning")


def test_valid_complete_item() -> None:
    """Test that complete valid item has no errors or warnings"""
    print("\nTesting complete valid Item...")
    validator = OmekaValidator("https://example.com")
    item = create_minimal_item(100)
    validator.validate_item(item)
    # Should have no errors or warnings
    assert len(validator.errors) == 0, f"Unexpected errors: {validator.errors}"
    assert len(validator.warnings) == 0, f"Unexpected warnings: {validator.warnings}"
    print("  ✓ Complete valid item has no errors or warnings")


def test_valid_complete_media() -> None:
    """Test that complete valid media has no errors or warnings"""
    print("\nTesting complete valid Media...")
    validator = OmekaValidator("https://example.com")
    media = create_minimal_media(100)
    validator.validate_media(media)
    # Should have no errors or warnings
    assert len(validator.errors) == 0, f"Unexpected errors: {validator.errors}"
    assert len(validator.warnings) == 0, f"Unexpected warnings: {validator.warnings}"
    print("  ✓ Complete valid media has no errors or warnings")


def test_duplicate_identifiers() -> None:
    """Test that duplicate identifiers generate errors"""
    print("\nTesting duplicate identifiers...")

    # Test duplicate item identifiers
    validator = OmekaValidator("https://example.com")
    item1 = create_minimal_item(201)
    item2 = create_minimal_item(202)
    # Give both items the same identifier
    item1["dcterms:identifier"][0]["@value"] = "duplicate_id_123"
    item2["dcterms:identifier"][0]["@value"] = "duplicate_id_123"

    validator.validate_item(item1)
    validator.validate_item(item2)
    validator._check_duplicate_identifiers()

    # Should have errors for both items
    duplicate_errors = [e for e in validator.errors if "Duplicate identifier" in str(e)]
    assert len(duplicate_errors) == 2, (
        f"Expected 2 duplicate errors, got {len(duplicate_errors)}"
    )
    assert any("201" in str(e) for e in duplicate_errors), "Expected error for item 201"
    assert any("202" in str(e) for e in duplicate_errors), "Expected error for item 202"
    print("  ✓ Duplicate item identifiers generate errors for all affected items")

    # Test duplicate media identifiers
    validator = OmekaValidator("https://example.com")
    media1 = create_minimal_media(301)
    media2 = create_minimal_media(302)
    media3 = create_minimal_media(303)
    # Give three media the same identifier
    media1["dcterms:identifier"][0]["@value"] = "duplicate_media_456"
    media2["dcterms:identifier"][0]["@value"] = "duplicate_media_456"
    media3["dcterms:identifier"][0]["@value"] = "duplicate_media_456"

    validator.validate_media(media1)
    validator.validate_media(media2)
    validator.validate_media(media3)
    validator._check_duplicate_identifiers()

    # Should have errors for all three media
    duplicate_errors = [e for e in validator.errors if "Duplicate identifier" in str(e)]
    assert len(duplicate_errors) == 3, (
        f"Expected 3 duplicate errors, got {len(duplicate_errors)}"
    )
    assert any("301" in str(e) for e in duplicate_errors), (
        "Expected error for media 301"
    )
    assert any("302" in str(e) for e in duplicate_errors), (
        "Expected error for media 302"
    )
    assert any("303" in str(e) for e in duplicate_errors), (
        "Expected error for media 303"
    )
    print("  ✓ Duplicate media identifiers generate errors for all affected media")

    # Test that unique identifiers don't generate errors
    validator = OmekaValidator("https://example.com")
    item1 = create_minimal_item(401)
    item2 = create_minimal_item(402)
    item1["dcterms:identifier"][0]["@value"] = "unique_id_1"
    item2["dcterms:identifier"][0]["@value"] = "unique_id_2"

    validator.validate_item(item1)
    validator.validate_item(item2)
    validator._check_duplicate_identifiers()

    duplicate_errors = [e for e in validator.errors if "Duplicate identifier" in str(e)]
    assert len(duplicate_errors) == 0, (
        f"Expected no duplicate errors, got {duplicate_errors}"
    )
    print("  ✓ Unique identifiers do not generate duplicate errors")


if __name__ == "__main__":
    try:
        test_item_errors()
        test_item_warnings()
        test_media_errors()
        test_media_warnings()
        test_valid_complete_item()
        test_valid_complete_media()
        test_duplicate_identifiers()
        print("\n✓ All issue #16 validation tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
