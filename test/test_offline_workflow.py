"""Test offline workflow functionality."""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from src.api import OmekaAPI


def test_validate_offline_files() -> bool:
    """Test validating offline files."""
    print("\nTest 1: Validate offline files")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create sample valid items
        items = [
            {
                "@context": "http://omeka.org/s/vocabs/o#",
                "@id": "https://omeka.unibe.ch/api/items/1",
                "@type": ["o:Item"],
                "o:id": 1,
                "o:is_public": True,
                "o:title": "Test Item",
                "o:created": {
                    "@value": "2025-01-15T10:00:00+00:00",
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                },
                "o:modified": {
                    "@value": "2025-01-15T10:00:00+00:00",
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
                        "@value": "test001",
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
            }
        ]

        # Create sample valid media
        media = [
            {
                "@context": "http://omeka.org/s/vocabs/o#",
                "@id": "https://omeka.unibe.ch/api/media/1",
                "@type": ["o:Media"],
                "o:id": 1,
                "o:is_public": True,
                "o:title": "Test Media",
                "o:created": {
                    "@value": "2025-01-15T10:00:00+00:00",
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                },
                "o:modified": {
                    "@value": "2025-01-15T10:00:00+00:00",
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                },
                "o:ingester": "upload",
                "o:renderer": "file",
                "o:item": {"@id": "https://omeka.unibe.ch/api/items/1", "o:id": 1},
                "o:media_type": "image/jpeg",
                "dcterms:identifier": [
                    {
                        "type": "literal",
                        "property_id": 10,
                        "property_label": "Identifier",
                        "is_public": True,
                        "@value": "media001",
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
            }
        ]

        # Save to files
        items_file = tmppath / "items.json"
        media_file = tmppath / "media.json"

        with open(items_file, "w") as f:
            json.dump(items, f, indent=2)

        with open(media_file, "w") as f:
            json.dump(media, f, indent=2)

        # Validate
        api = OmekaAPI("https://omeka.unibe.ch")
        result = api.validate_offline_files(tmppath)

        # Assert validation passed
        assert result["overall_valid"], (
            f"Validation should pass. Errors: items={result['items_errors']}, media={result['media_errors']}"
        )
        print(f"  ✓ Validated {result['items_validated']} items")
        print(f"  ✓ Validated {result['media_validated']} media")
        print("  ✓ All files are valid")


def test_validate_invalid_files() -> bool:
    """Test validating invalid offline files."""
    print("\nTest 2: Validate invalid offline files")
    print("=" * 60)

    with TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create sample invalid items (missing required fields)
        items = [
            {
                "@context": "http://omeka.org/s/vocabs/o#",
                "@id": "https://omeka.unibe.ch/api/items/1",
                "@type": ["o:Item"],
                "o:id": 1,
                "o:is_public": True,
                "o:title": "",  # Empty title - should fail
                "o:created": {
                    "@value": "2025-01-15T10:00:00+00:00",
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                },
                "o:modified": {
                    "@value": "2025-01-15T10:00:00+00:00",
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                },
                "o:media": [],
                "o:item_set": [],
                "o:site": [],
                # Missing dcterms:identifier
                "dcterms:title": [
                    {
                        "type": "literal",
                        "property_id": 1,
                        "property_label": "Title",
                        "is_public": True,
                        "@value": "Test",
                    }
                ],
            }
        ]

        # Save to files
        items_file = tmppath / "items.json"

        with open(items_file, "w") as f:
            json.dump(items, f, indent=2)

        # Validate
        api = OmekaAPI("https://omeka.unibe.ch")
        result = api.validate_offline_files(tmppath)

        # Assert validation detected errors
        assert not result["overall_valid"], (
            "Validation should have failed for invalid items"
        )
        assert len(result["items_errors"]) > 0 or len(result["media_errors"]) > 0, (
            "Should have detected validation errors"
        )
        print(f"  ✓ Correctly detected {len(result['items_errors'])} invalid item(s)")


def test_update_methods_dry_run() -> bool:
    """Test update methods in dry-run mode."""
    print("\nTest 3: Update methods (dry run)")
    print("=" * 60)

    # Create sample valid item
    item_data = {
        "@context": "http://omeka.org/s/vocabs/o#",
        "@id": "https://omeka.unibe.ch/api/items/1",
        "@type": ["o:Item"],
        "o:id": 1,
        "o:is_public": True,
        "o:title": "Test Item",
        "o:created": {
            "@value": "2025-01-15T10:00:00+00:00",
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
        },
        "o:modified": {
            "@value": "2025-01-15T10:00:00+00:00",
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
                "@value": "test001",
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
    }

    api = OmekaAPI("https://omeka.unibe.ch")
    result = api.update_item(1, item_data, dry_run=True)

    assert result["validation_passed"], "Dry run validation should pass"
    assert result["dry_run"], "Should be marked as dry run"
    assert not result["updated"], "No changes should be made in dry run"
    print("  ✓ Dry run validation passed")
    print("  ✓ No changes were made")


if __name__ == "__main__":
    print("Testing offline workflow functionality")
    print("=" * 60)

    all_passed = True

    all_passed &= test_validate_offline_files()
    all_passed &= test_validate_invalid_files()
    all_passed &= test_update_methods_dry_run()

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All offline workflow tests passed!")
        sys.exit(0)
    else:
        print("✗ Some offline workflow tests failed")
        sys.exit(1)
