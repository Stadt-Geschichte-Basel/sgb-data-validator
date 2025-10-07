"""Test the OmekaAPI module"""

from pathlib import Path
from unittest.mock import Mock, patch

from src.api import OmekaAPI


def test_api_initialization():
    """Test API client initialization"""
    api = OmekaAPI(
        "https://omeka.unibe.ch",
        key_identity="test_identity",
        key_credential="test_credential",
    )
    assert api.base_url == "https://omeka.unibe.ch"
    assert api.key_identity == "test_identity"
    assert api.key_credential == "test_credential"
    api.close()
    print("✓ API initialization test passed")


def test_api_context_manager():
    """Test API as context manager"""
    with OmekaAPI("https://omeka.unibe.ch") as api:
        assert api.base_url == "https://omeka.unibe.ch"
    print("✓ API context manager test passed")


def test_validate_item_valid():
    """Test validating a valid item"""
    api = OmekaAPI("https://omeka.unibe.ch")

    valid_item = {
        "@context": "https://omeka.unibe.ch/api-context",
        "@id": "https://omeka.unibe.ch/api/items/10777",
        "@type": "o:Item",
        "o:id": 10777,
        "o:is_public": True,
        "o:title": "Test Item",
        "o:created": {"@value": "2024-01-01T00:00:00+00:00", "@type": "dateTime"},
        "o:modified": {"@value": "2024-01-01T00:00:00+00:00", "@type": "dateTime"},
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
    }

    is_valid, errors = api.validate_item(valid_item)
    assert is_valid is True
    assert len(errors) == 0
    api.close()
    print("✓ Valid item validation test passed")


def test_validate_item_invalid():
    """Test validating an invalid item"""
    api = OmekaAPI("https://omeka.unibe.ch")

    invalid_item = {
        "@context": "https://omeka.unibe.ch/api-context",
        "@id": "https://omeka.unibe.ch/api/items/10777",
        "@type": "o:Item",
        "o:id": 10777,
        # Missing required fields
    }

    is_valid, errors = api.validate_item(invalid_item)
    assert is_valid is False
    assert len(errors) > 0
    api.close()
    print("✓ Invalid item validation test passed")


def test_save_and_load_file():
    """Test saving and loading data to/from files"""
    import tempfile

    api = OmekaAPI("https://omeka.unibe.ch")

    test_data = {"test": "data", "items": [1, 2, 3]}

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test.json"

        # Save
        api.save_to_file(test_data, test_file)
        assert test_file.exists()

        # Load
        loaded_data = api.load_from_file(test_file)
        assert loaded_data == test_data

    api.close()
    print("✓ Save and load file test passed")


@patch("httpx.Client.get")
def test_get_item_set(mock_get):
    """Test getting an item set"""
    api = OmekaAPI("https://omeka.unibe.ch")

    mock_response = Mock()
    mock_response.json.return_value = {"o:id": 10780, "o:title": "Test Set"}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = api.get_item_set(10780)
    assert result["o:id"] == 10780
    assert result["o:title"] == "Test Set"
    mock_get.assert_called_once()
    api.close()
    print("✓ Get item set test passed")


@patch("httpx.Client.get")
def test_get_items_from_set_single_page(mock_get):
    """Test getting items from a set with single page"""
    api = OmekaAPI("https://omeka.unibe.ch")

    mock_response = Mock()
    mock_response.json.return_value = [
        {"o:id": 1, "o:title": "Item 1"},
        {"o:id": 2, "o:title": "Item 2"},
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = api.get_items_from_set(10780, page=1)
    assert len(result) == 2
    assert result[0]["o:id"] == 1
    api.close()
    print("✓ Get items from set test passed")


@patch("httpx.Client.get")
def test_get_media_from_item(mock_get):
    """Test getting media from an item"""
    api = OmekaAPI("https://omeka.unibe.ch")

    mock_response = Mock()
    mock_response.json.return_value = [
        {"o:id": 100, "o:media_type": "image/jpeg"},
        {"o:id": 101, "o:media_type": "image/png"},
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = api.get_media_from_item(10777)
    assert len(result) == 2
    assert result[0]["o:media_type"] == "image/jpeg"
    api.close()
    print("✓ Get media from item test passed")


if __name__ == "__main__":
    print("Running OmekaAPI tests...")
    print()
    test_api_initialization()
    test_api_context_manager()
    test_validate_item_valid()
    test_validate_item_invalid()
    test_save_and_load_file()
    test_get_item_set()
    test_get_items_from_set_single_page()
    test_get_media_from_item()
    print()
    print("✓ All tests passed!")
