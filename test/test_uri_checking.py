"""Test URI checking functionality"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validate import OmekaValidator, DataValidationError, DataValidationWarning


def test_extract_uris():
    """Test URI extraction from item/media data"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=False)

    # Sample item data with URIs
    item_data = {
        "o:id": 12345,
        "dcterms:creator": [
            {"@id": "https://www.wikidata.org/wiki/Q123", "o:label": "Test Creator"}
        ],
        "dcterms:source": [
            {"@id": "https://example.com/source", "o:label": "Test Source"}
        ],
        "dcterms:title": [{"@value": "Test Title"}],
    }

    uris = validator.extract_uris_from_data(item_data)
    assert len(uris) == 2
    assert ("dcterms:creator[0].@id", "https://www.wikidata.org/wiki/Q123") in uris
    assert ("dcterms:source[0].@id", "https://example.com/source") in uris


def test_extract_media_uri():
    """Test URI extraction from media data"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=False)

    # Sample media data with original URL
    media_data = {
        "o:id": 67890,
        "o:original_url": "https://example.com/media/image.jpg",
        "dcterms:title": [{"@value": "Test Media"}],
    }

    uris = validator.extract_uris_from_data(media_data)
    assert len(uris) == 1
    assert ("o:original_url", "https://example.com/media/image.jpg") in uris


@pytest.mark.asyncio
async def test_check_valid_uri():
    """Test checking a valid URI"""
    validator = OmekaValidator(
        "https://omeka.unibe.ch", check_uris=True, uri_check_severity="warning"
    )

    # Check a valid URI (example.com should always be reachable)
    await validator.check_uri_async(
        "https://example.com", "Item", 12345, "dcterms:source[0].@id"
    )

    # Should not have errors or warnings for a valid URI
    assert len(validator.errors) == 0
    # Note: might have warnings if there's a redirect, but that's expected


@pytest.mark.asyncio
async def test_check_invalid_uri():
    """Test checking an invalid URI (404)"""
    validator = OmekaValidator(
        "https://omeka.unibe.ch", check_uris=True, uri_check_severity="warning"
    )

    # Check a URI that definitely doesn't exist (invalid domain)
    await validator.check_uri_async(
        "https://this-domain-definitely-does-not-exist-12345.com/test",
        "Item",
        12345,
        "dcterms:source[0].@id",
    )

    # Should have a warning for the failed URI
    assert validator.failed_uris == 1
    assert len(validator.warnings) == 1


@pytest.mark.asyncio
async def test_check_invalid_uri_as_error():
    """Test checking an invalid URI with error severity"""
    validator = OmekaValidator(
        "https://omeka.unibe.ch", check_uris=True, uri_check_severity="error"
    )

    # Check a URI that definitely doesn't exist (invalid domain)
    await validator.check_uri_async(
        "https://another-nonexistent-domain-67890.invalid/test",
        "Media",
        67890,
        "o:original_url",
    )

    # Should have an error for the failed URI
    assert validator.failed_uris == 1
    assert len(validator.errors) == 1


def run_async_test(test_func):
    """Helper to run async tests"""
    asyncio.run(test_func())


if __name__ == "__main__":
    print("Running URI checking tests...")

    print("✓ Test: extract_uris")
    test_extract_uris()

    print("✓ Test: extract_media_uri")
    test_extract_media_uri()

    print("✓ Test: check_valid_uri")
    run_async_test(test_check_valid_uri)

    print("✓ Test: check_invalid_uri (warning)")
    run_async_test(test_check_invalid_uri)

    print("✓ Test: check_invalid_uri_as_error")
    run_async_test(test_check_invalid_uri_as_error)

    print("\n✅ All URI checking tests passed!")
