"""Test private flag propagation from media to items (Issue #36).

Tests that:
1. Media with placeholder images get o:is_public=False
2. Items inherit o:is_public=False if any of their media children are private
"""

from src.transformations import (
    has_placeholder_media,
    propagate_private_flag_to_items,
    set_media_private_flag,
    transform_item_set_data,
    transform_media,
)


def test_has_placeholder_media_detection() -> None:
    """Test that placeholder media are correctly detected."""
    print("\nTest 1: Placeholder media detection")
    print("=" * 60)

    # Media with placeholder
    media_with_placeholder = {
        "o:id": 1,
        "o:filename": "image-sgb-fdp-platzhalter-01.jpg",
        "o:is_public": True,
    }

    # Regular media
    regular_media = {
        "o:id": 2,
        "o:filename": "regular-image.jpg",
        "o:is_public": True,
    }

    assert has_placeholder_media(media_with_placeholder) is True
    print("  ✓ Placeholder media detected")

    assert has_placeholder_media(regular_media) is False
    print("  ✓ Regular media not detected as placeholder")


def test_set_media_private_flag() -> None:
    """Test that media private flag is set correctly."""
    print("\nTest 2: Set media private flag")
    print("=" * 60)

    # Media with placeholder should become private
    media_with_placeholder = {
        "o:id": 1,
        "o:filename": "sgb-fdp-platzhalter.jpg",
        "o:is_public": True,
        "o:title": "Test",
    }

    result = set_media_private_flag(media_with_placeholder)
    assert result["o:is_public"] is False
    print("  ✓ Media with placeholder set to private")

    # Regular media should stay public
    regular_media = {
        "o:id": 2,
        "o:filename": "regular.jpg",
        "o:is_public": True,
        "o:title": "Test",
    }

    result = set_media_private_flag(regular_media)
    assert result["o:is_public"] is True
    print("  ✓ Regular media stays public")

    # Already private media should stay private
    already_private = {
        "o:id": 3,
        "o:filename": "regular.jpg",
        "o:is_public": False,
        "o:title": "Test",
    }

    result = set_media_private_flag(already_private)
    assert result["o:is_public"] is False
    print("  ✓ Already private media stays private")


def test_propagate_private_flag_single_child() -> None:
    """Test propagation with single private child."""
    print("\nTest 3: Propagate flag with single private child")
    print("=" * 60)

    items = [
        {"o:id": 100, "o:is_public": True, "o:title": "Item 1"},
        {"o:id": 200, "o:is_public": True, "o:title": "Item 2"},
    ]

    media = [
        {
            "o:id": 1,
            "o:is_public": False,  # Private media
            "o:item": {"o:id": 100},  # Belongs to Item 1
        },
        {
            "o:id": 2,
            "o:is_public": True,  # Public media
            "o:item": {"o:id": 200},  # Belongs to Item 2
        },
    ]

    result = propagate_private_flag_to_items(items, media)

    # Item 1 should be private (has private media)
    assert result[0]["o:is_public"] is False
    print("  ✓ Item with private media became private")

    # Item 2 should stay public (all media public)
    assert result[1]["o:is_public"] is True
    print("  ✓ Item with only public media stays public")


def test_propagate_private_flag_multiple_children() -> None:
    """Test propagation with multiple children, one private."""
    print("\nTest 4: Propagate flag with multiple children")
    print("=" * 60)

    items = [
        {"o:id": 100, "o:is_public": True, "o:title": "Item with mixed media"}
    ]

    media = [
        {
            "o:id": 1,
            "o:is_public": True,  # Public media
            "o:item": {"o:id": 100},
        },
        {
            "o:id": 2,
            "o:is_public": True,  # Public media
            "o:item": {"o:id": 100},
        },
        {
            "o:id": 3,
            "o:is_public": False,  # One private media
            "o:item": {"o:id": 100},
        },
    ]

    result = propagate_private_flag_to_items(items, media)

    # Item should be private because one of its media is private
    assert result[0]["o:is_public"] is False
    print("  ✓ Item with one private media (among many) became private")


def test_propagate_private_flag_no_media() -> None:
    """Test propagation when item has no media."""
    print("\nTest 5: Propagate flag with no media")
    print("=" * 60)

    items = [{"o:id": 100, "o:is_public": True, "o:title": "Item without media"}]

    media: list = []

    result = propagate_private_flag_to_items(items, media)

    # Item should stay public (no private media)
    assert result[0]["o:is_public"] is True
    print("  ✓ Item without media stays public")


def test_transform_media_sets_private_flag() -> None:
    """Test that transform_media automatically sets private flag."""
    print("\nTest 6: Transform media sets private flag")
    print("=" * 60)

    media_data = {
        "o:id": 1,
        "o:filename": "sgb-fdp-platzhalter.jpg",
        "o:is_public": True,
        "o:title": "Test  Media",  # Extra spaces to test transformation
        "dcterms:title": [
            {
                "type": "literal",
                "@value": "Test  Title",
                "property_id": 1,
            }
        ],
    }

    result = transform_media(media_data)

    # Should be private due to placeholder
    assert result["o:is_public"] is False
    print("  ✓ Transform media sets private flag for placeholder")

    # Should also transform text
    assert result["o:title"] == "Test Media"
    print("  ✓ Transform media also applies text transformations")


def test_transform_item_set_complete_workflow() -> None:
    """Test complete workflow with transform_item_set_data."""
    print("\nTest 7: Complete transformation workflow")
    print("=" * 60)

    item_set_data = {"o:id": 1, "o:title": "Test Set"}

    items = [
        {"o:id": 100, "o:is_public": True, "o:title": "Item 1"},
        {"o:id": 200, "o:is_public": True, "o:title": "Item 2"},
        {"o:id": 300, "o:is_public": True, "o:title": "Item 3"},
    ]

    media = [
        {
            "o:id": 1,
            "o:filename": "sgb-fdp-platzhalter.jpg",  # Placeholder
            "o:is_public": True,
            "o:item": {"o:id": 100},
            "o:title": "Media 1",
        },
        {
            "o:id": 2,
            "o:filename": "regular.jpg",
            "o:is_public": True,
            "o:item": {"o:id": 200},
            "o:title": "Media 2",
        },
        {
            "o:id": 3,
            "o:filename": "another-regular.jpg",
            "o:is_public": True,
            "o:item": {"o:id": 200},  # Item 2 has 2 media
            "o:title": "Media 3",
        },
    ]

    _, result_items, result_media = transform_item_set_data(
        item_set_data, items, media
    )

    # Media 1 should be private (has placeholder)
    assert result_media[0]["o:is_public"] is False
    print("  ✓ Media with placeholder is private")

    # Media 2 and 3 should stay public
    assert result_media[1]["o:is_public"] is True
    assert result_media[2]["o:is_public"] is True
    print("  ✓ Regular media stay public")

    # Item 1 should be private (has private media)
    assert result_items[0]["o:is_public"] is False
    print("  ✓ Item 1 is private (has private media)")

    # Item 2 should stay public (all media public)
    assert result_items[1]["o:is_public"] is True
    print("  ✓ Item 2 is public (all media public)")

    # Item 3 should stay public (no media)
    assert result_items[2]["o:is_public"] is True
    print("  ✓ Item 3 is public (no media)")


def test_edge_cases() -> None:
    """Test edge cases and error handling."""
    print("\nTest 8: Edge cases")
    print("=" * 60)

    # Empty lists
    result = propagate_private_flag_to_items([], [])
    assert result == []
    print("  ✓ Empty lists handled correctly")

    # Media without o:item
    items = [{"o:id": 100, "o:is_public": True}]
    media = [{"o:id": 1, "o:is_public": False}]  # No o:item field

    result = propagate_private_flag_to_items(items, media)
    assert result[0]["o:is_public"] is True  # Should stay public
    print("  ✓ Media without o:item doesn't affect items")

    # Non-dict items
    result = set_media_private_flag(None)
    assert result is None
    print("  ✓ None value handled correctly")

    result = set_media_private_flag("not a dict")
    assert result == "not a dict"
    print("  ✓ Non-dict value handled correctly")


def run_all_tests() -> None:
    """Run all tests for issue #36."""
    print("\n" + "=" * 60)
    print("Testing Private Flag Propagation (Issue #36)")
    print("=" * 60)

    test_has_placeholder_media_detection()
    test_set_media_private_flag()
    test_propagate_private_flag_single_child()
    test_propagate_private_flag_multiple_children()
    test_propagate_private_flag_no_media()
    test_transform_media_sets_private_flag()
    test_transform_item_set_complete_workflow()
    test_edge_cases()

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
