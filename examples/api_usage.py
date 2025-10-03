"""
Example usage of the Omeka S API module.

This script demonstrates how to use the API for:
- Reading item sets, items, and media
- Saving data to files
- Validating data
- Creating backups
"""

from pathlib import Path

from src.api import OmekaAPI


def main() -> None:
    """Demonstrate API usage"""
    # Initialize the API client
    base_url = "https://omeka.unibe.ch"
    api_key = None  # Optional: Add your API key here

    with OmekaAPI(base_url, api_key) as api:
        # Example 1: Read an item set
        print("=" * 70)
        print("Example 1: Reading an item set")
        print("=" * 70)
        item_set_id = 10780
        item_set = api.get_item_set(item_set_id)
        print(f"Item Set Title: {item_set.get('o:title')}")
        print(f"Item Set ID: {item_set.get('o:id')}")
        print()

        # Example 2: Get items from a set (first page only)
        print("=" * 70)
        print("Example 2: Getting items from a set (first page)")
        print("=" * 70)
        items = api.get_items_from_set(item_set_id, page=1, per_page=5)
        print(f"Retrieved {len(items)} items")
        for item in items[:3]:  # Show first 3
            print(f"  - {item.get('o:title')} (ID: {item.get('o:id')})")
        print()

        # Example 3: Get a specific item and its media
        print("=" * 70)
        print("Example 3: Getting a specific item and its media")
        print("=" * 70)
        if items:
            item_id = items[0].get("o:id")
            item = api.get_item(item_id)
            print(f"Item: {item.get('o:title')}")

            media_list = api.get_media_from_item(item_id)
            print(f"Found {len(media_list)} media files")
            for media in media_list[:2]:  # Show first 2
                print(f"  - {media.get('o:title')} ({media.get('o:media_type')})")
        print()

        # Example 4: Save data to a file
        print("=" * 70)
        print("Example 4: Saving data to a file")
        print("=" * 70)
        output_dir = Path("examples/output")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save the item set
        api.save_to_file(item_set, output_dir / "item_set.json")
        print(f"Saved item set to: {output_dir / 'item_set.json'}")

        # Save items
        api.save_to_file(items, output_dir / "items_sample.json")
        print(f"Saved items to: {output_dir / 'items_sample.json'}")
        print()

        # Example 5: Validate an item
        print("=" * 70)
        print("Example 5: Validating an item")
        print("=" * 70)
        if items:
            item_data = items[0]
            is_valid, errors = api.validate_item(item_data)
            print(f"Item {item_data.get('o:id')} valid: {is_valid}")
            if not is_valid:
                print("Errors:")
                for error in errors:
                    print(f"  - {error}")
        print()

        print("=" * 70)
        print("Examples completed successfully!")
        print("=" * 70)
        print()
        print("For more advanced usage, see the API documentation in src/api.py")


if __name__ == "__main__":
    main()
