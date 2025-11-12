"""Test creation methods for migration support"""

import pytest

from src.api import OmekaAPI


def test_create_item_validation():
    """Test that create_item validates data correctly"""
    api = OmekaAPI("https://example.com")

    # Valid item data (without o:id)
    valid_item = {
        "o:item_set": [{"o:id": 123}],
        "dcterms:title": [{"type": "literal", "property_id": 1, "@value": "Test"}],
    }

    result = api.create_item(valid_item, dry_run=True)

    assert result["validation_passed"] is True
    assert result["dry_run"] is True
    assert result["created"] is False
    assert result["item_id"] is None
    assert "validation passed" in result["message"]


def test_create_item_removes_id():
    """Test that create_item removes o:id if present"""
    api = OmekaAPI("https://example.com")

    # Item with o:id (should be removed)
    item_with_id = {
        "o:id": 999,  # Should be removed
        "o:item_set": [{"o:id": 123}],
        "dcterms:title": [{"type": "literal", "property_id": 1, "@value": "Test"}],
    }

    result = api.create_item(item_with_id, dry_run=True)

    # Should still validate (ID removed automatically)
    assert result["validation_passed"] is True


def test_create_item_requires_auth():
    """Test that create_item requires authentication for actual creation"""
    api = OmekaAPI("https://example.com")  # No auth

    valid_item = {
        "o:item_set": [{"o:id": 123}],
        "dcterms:title": [{"type": "literal", "property_id": 1, "@value": "Test"}],
    }

    result = api.create_item(valid_item, dry_run=False)

    assert result["created"] is False
    assert "Authentication required" in result["message"]


def test_create_media_validation():
    """Test that create_media validates data correctly"""
    api = OmekaAPI("https://example.com")

    # Valid media data (without o:id)
    valid_media = {
        "o:item": {"o:id": 121200},
        "o:ingester": "url",
        "o:source": "https://example.com/image.jpg",
        "ingest_url": "https://example.com/image.jpg",
    }

    result = api.create_media(valid_media, dry_run=True)

    assert result["validation_passed"] is True
    assert result["dry_run"] is True
    assert result["created"] is False
    assert result["media_id"] is None


def test_create_media_requires_item():
    """Test that create_media requires o:item reference"""
    api = OmekaAPI("https://example.com")

    # Media without o:item (should fail validation)
    invalid_media = {
        "o:ingester": "url",
        "o:source": "https://example.com/image.jpg",
    }

    result = api.create_media(invalid_media, dry_run=True)

    assert result["validation_passed"] is False
    assert len(result["errors"]) > 0


def test_migrate_item_set_missing_files():
    """Test that migrate_item_set handles missing files gracefully"""
    api = OmekaAPI("https://example.com")

    result = api.migrate_item_set(
        source_dir="/nonexistent/path",
        target_item_set_id=456,
        dry_run=True,
    )

    assert result["items_processed"] == 0
    assert len(result["errors"]) > 0
    assert "not found" in result["errors"][0]


def test_migrate_item_set_requires_auth():
    """Test that migrate_item_set requires authentication for actual migration"""
    import json
    import tempfile
    from pathlib import Path

    api = OmekaAPI("https://example.com")  # No auth

    # Create temporary directory with test data
    with tempfile.TemporaryDirectory() as tmpdir:
        items_file = Path(tmpdir) / "items.json"
        items_file.write_text(
            json.dumps(
                [
                    {
                        "o:id": 123,
                        "o:item_set": [{"o:id": 10780}],
                        "dcterms:title": [
                            {
                                "type": "literal",
                                "property_id": 1,
                                "@value": "Test Item",
                            }
                        ],
                    }
                ]
            )
        )

        result = api.migrate_item_set(
            source_dir=tmpdir,
            target_item_set_id=456,
            dry_run=False,
        )

        assert result["items_processed"] == 0
        assert "Authentication required" in result["errors"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
