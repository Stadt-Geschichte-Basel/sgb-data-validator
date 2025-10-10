"""Test validation for URLs in literal fields (issue #22)"""

import sys

from validate import OmekaValidator


def create_item_with_literal_field(
    item_id: int, field_name: str, field_value: str
) -> dict:
    """Create a minimal item with a specific literal field value"""
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
        field_name: [
            {
                "type": "literal",
                "property_id": 99,
                "property_label": field_name,
                "is_public": True,
                "@value": field_value,
            }
        ],
    }


def create_media_with_literal_field(
    media_id: int, field_name: str, field_value: str
) -> dict:
    """Create a minimal media with a specific literal field value"""
    return {
        "@context": "https://omeka.unibe.ch/api-context",
        "@id": f"https://omeka.unibe.ch/api/media/{media_id}",
        "@type": "o:Media",
        "o:id": media_id,
        "o:is_public": True,
        "o:owner": {"@id": "https://omeka.unibe.ch/api/users/1", "o:id": 1},
        "o:resource_class": None,
        "o:resource_template": {
            "@id": "https://omeka.unibe.ch/api/resource_templates/33",
            "o:id": 33,
        },
        "o:thumbnail": None,
        "o:title": "Test Media",
        "thumbnail_display_urls": {},
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
        "dcterms:identifier": [
            {
                "type": "literal",
                "property_id": 10,
                "property_label": "Identifier",
                "is_public": True,
                "@value": "media123",
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
                "@value": "Public Domain",
            }
        ],
        "dcterms:license": [
            {
                "type": "uri",
                "property_id": 16,
                "property_label": "License",
                "is_public": True,
                "@id": "https://creativecommons.org/publicdomain/mark/1.0/",
            }
        ],
        field_name: [
            {
                "type": "literal",
                "property_id": 99,
                "property_label": field_name,
                "is_public": True,
                "@value": field_value,
            }
        ],
    }


def test_url_detection_in_literal_fields():
    """Test that URLs in literal fields generate warnings"""
    print("\nTest 1: URL detection in literal fields")
    print("=" * 60)

    # Test with various URL patterns
    test_cases = [
        ("https://example.com", True, "Full HTTPS URL"),
        ("http://example.com", True, "Full HTTP URL"),
        ("www.example.com", True, "www. prefix"),
        ("ftp://files.example.com", True, "FTP URL"),
        ("Visit https://example.com for more", True, "URL in text"),
        ("Check www.example.com/path", True, "www. URL with path"),
        ("See http://example.com?param=value", True, "URL with query params"),
        ("Plain text without URLs", False, "Plain text"),
        ("example.com", False, "Domain without protocol"),
        ("Contact us at info@example.com", False, "Email address"),
    ]

    validator = OmekaValidator(base_url="https://test.example.com")

    for field_value, should_warn, description in test_cases:
        validator.warnings = []  # Reset warnings
        validator.errors = []

        item = create_item_with_literal_field(1, "dcterms:isPartOf", field_value)
        validator.validate_item(item)

        has_url_warning = any(
            "Literal field contains URL" in str(warning)
            for warning in validator.warnings
        )

        if should_warn and has_url_warning:
            print(f"  ✓ {description}: Correctly detected URL in '{field_value[:50]}'")
        elif not should_warn and not has_url_warning:
            print(f"  ✓ {description}: Correctly accepted '{field_value[:50]}'")
        elif should_warn and not has_url_warning:
            print(f"  ✗ {description}: Failed to detect URL in '{field_value[:50]}'")
            return False
        else:
            print(f"  ✗ {description}: False positive for '{field_value[:50]}'")
            return False

    return True


def test_url_in_item_fields():
    """Test URL detection in various item fields"""
    print("\nTest 2: URL detection in item fields")
    print("=" * 60)

    validator = OmekaValidator(base_url="https://test.example.com")

    # Test dcterms:description with URL
    item = create_item_with_literal_field(
        2,
        "dcterms:description",
        "This is a description with a URL: https://example.com/resource",
    )
    validator.validate_item(item)

    url_warnings = [
        w for w in validator.warnings if "Literal field contains URL" in str(w)
    ]
    if len(url_warnings) > 0:
        print("  ✓ Detected URL in dcterms:description")
        print(f"    Warning: {url_warnings[0]}")
    else:
        print("  ✗ Failed to detect URL in dcterms:description")
        return False

    # Test dcterms:isPartOf with URL
    validator.warnings = []
    validator.errors = []
    item = create_item_with_literal_field(
        3, "dcterms:isPartOf", "See www.stadtgeschichtebasel.ch for details"
    )
    validator.validate_item(item)

    url_warnings = [
        w for w in validator.warnings if "Literal field contains URL" in str(w)
    ]
    if len(url_warnings) > 0:
        print("  ✓ Detected URL in dcterms:isPartOf")
    else:
        print("  ✗ Failed to detect URL in dcterms:isPartOf")
        return False

    return True


def test_url_in_media_fields():
    """Test URL detection in media fields"""
    print("\nTest 3: URL detection in media fields")
    print("=" * 60)

    validator = OmekaValidator(base_url="https://test.example.com")

    # Test dcterms:creator with URL
    media = create_media_with_literal_field(
        10, "dcterms:creator", "Visit http://artist-website.com for portfolio"
    )
    validator.validate_media(media)

    url_warnings = [
        w for w in validator.warnings if "Literal field contains URL" in str(w)
    ]
    if len(url_warnings) > 0:
        print("  ✓ Detected URL in dcterms:creator")
        print(f"    Warning: {url_warnings[0]}")
    else:
        print("  ✗ Failed to detect URL in dcterms:creator")
        return False

    return True


def test_no_warning_for_uri_fields():
    """Test that URI type fields don't generate warnings"""
    print("\nTest 4: No warnings for URI type fields")
    print("=" * 60)

    validator = OmekaValidator(base_url="https://test.example.com")

    # Create an item with URI field (not literal)
    item = {
        "@context": "https://omeka.unibe.ch/api-context",
        "@id": "https://omeka.unibe.ch/api/items/100",
        "@type": "o:Item",
        "o:id": 100,
        "o:is_public": True,
        "o:owner": {"@id": "https://omeka.unibe.ch/api/users/1", "o:id": 1},
        "o:resource_class": None,
        "o:resource_template": None,
        "o:thumbnail": None,
        "o:title": "Test Item",
        "thumbnail_display_urls": {},
        "o:created": {
            "@value": "2024-01-01T00:00:00+00:00",
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
        },
        "o:modified": {
            "@value": "2024-01-01T00:00:00+00:00",
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
        },
        "o:media": [],
        "o:item_set": [],
        "o:site": [],
        "dcterms:identifier": [
            {
                "type": "literal",
                "property_id": 10,
                "property_label": "Identifier",
                "is_public": True,
                "@value": "test456",
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
        "dcterms:creator": [
            {
                "type": "uri",  # URI field, not literal
                "property_id": 2,
                "property_label": "Creator",
                "is_public": True,
                "@id": "https://example.com/creator/123",
                "o:label": "Creator Name",
            }
        ],
    }

    validator.validate_item(item)

    url_warnings = [
        w for w in validator.warnings if "Literal field contains URL" in str(w)
    ]
    if len(url_warnings) == 0:
        print("  ✓ No warnings for URI type fields (as expected)")
    else:
        print("  ✗ Unexpected warnings for URI type fields")
        print(f"    Warnings: {url_warnings}")
        return False

    return True


def test_multiple_urls_in_field():
    """Test detection of multiple URLs in a single field"""
    print("\nTest 5: Multiple URLs in a single field")
    print("=" * 60)

    validator = OmekaValidator(base_url="https://test.example.com")

    item = create_item_with_literal_field(
        5,
        "dcterms:description",
        "Visit https://example.com and http://another.com for more information",
    )
    validator.validate_item(item)

    url_warnings = [
        w for w in validator.warnings if "Literal field contains URL" in str(w)
    ]
    if len(url_warnings) > 0:
        print("  ✓ Detected multiple URLs in field")
        print(f"    Warning: {url_warnings[0]}")
    else:
        print("  ✗ Failed to detect multiple URLs")
        return False

    return True


if __name__ == "__main__":
    print("Testing URL detection in literal fields (Issue #22)")
    print("=" * 60)

    all_passed = True

    all_passed &= test_url_detection_in_literal_fields()
    all_passed &= test_url_in_item_fields()
    all_passed &= test_url_in_media_fields()
    all_passed &= test_no_warning_for_uri_fields()
    all_passed &= test_multiple_urls_in_field()

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
