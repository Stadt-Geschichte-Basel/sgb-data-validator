"""
Migration Usage Examples

This module demonstrates how to use the creation methods for migrating
data between Omeka S instances or creating copies within the same instance.

The creation methods enable true data migration where resources are created
with new IDs rather than updating existing resources.
"""

from pathlib import Path

from src.api import OmekaAPI


def example_1_create_single_item():
    """Example 1: Create a single new item"""
    print("\n" + "=" * 70)
    print("Example 1: Create a Single New Item")
    print("=" * 70)

    api = OmekaAPI(
        base_url="https://example.com",
        key_identity="your_key_identity",
        key_credential="your_key_credential",
    )

    # Item data (without o:id - will be assigned by server)
    item_data = {
        "o:item_set": [{"o:id": 123}],
        "dcterms:title": [{"type": "literal", "property_id": 1, "@value": "New Item"}],
        "dcterms:description": [
            {
                "type": "literal",
                "property_id": 4,
                "@value": "Created via API",
            }
        ],
    }

    # First validate (dry run)
    result = api.create_item(item_data, dry_run=True)
    print(f"Validation: {result['validation_passed']}")

    if result["validation_passed"]:
        # Create for real
        result = api.create_item(item_data, dry_run=False)
        if result["created"]:
            print(f"✅ Item created with ID: {result['item_id']}")
        else:
            print(f"❌ Creation failed: {result['message']}")


def example_2_migrate_complete_item_set():
    """Example 2: Migrate a complete item set to new instance"""
    print("\n" + "=" * 70)
    print("Example 2: Migrate Complete Item Set")
    print("=" * 70)

    # Source instance (download)
    source_api = OmekaAPI(base_url="https://source.example.com")
    source_item_set_id = 10780

    # Download from source
    download_dir = Path("data")
    download_result = source_api.download_item_set(
        item_set_id=source_item_set_id,
        output_dir=download_dir,
    )

    print("Downloaded:")
    print(f"  - Items: {download_result['items_downloaded']}")
    print(f"  - Media: {download_result['media_downloaded']}")

    source_dir = download_result["saved_to"]["directory"]

    # Apply transformations if needed
    transformed_dir = source_api.apply_transformations(
        input_dir=source_dir,
        output_dir=download_dir,
        apply_all_transformations=True,
    )

    # Target instance (create)
    target_api = OmekaAPI(
        base_url="https://target.example.com",
        key_identity="your_key_identity",
        key_credential="your_key_credential",
    )
    target_item_set_id = 456  # Different item set in target instance

    # First validate migration (dry run)
    print("\nValidating migration...")
    result = target_api.migrate_item_set(
        source_dir=transformed_dir,
        target_item_set_id=target_item_set_id,
        dry_run=True,
    )

    print(f"Items validated: {result['items_processed']}")
    print(f"Media validated: {result['media_processed']}")

    if result["errors"]:
        print(f"⚠️  Validation errors: {len(result['errors'])}")
        return

    # Perform actual migration
    print("\nPerforming migration...")
    result = target_api.migrate_item_set(
        source_dir=transformed_dir,
        target_item_set_id=target_item_set_id,
        dry_run=False,
    )

    print("\nMigration complete:")
    print(f"  ✅ Items created: {result['items_created']}/{result['items_processed']}")
    print(f"  ✅ Media created: {result['media_created']}/{result['media_processed']}")

    if result["items_failed"] or result["media_failed"]:
        print(f"  ❌ Failed items: {result['items_failed']}")
        print(f"  ❌ Failed media: {result['media_failed']}")

    # Show ID mapping for reference
    print("\nID Mapping:")
    print(f"  - Items mapped: {len(result['id_mapping']['items'])}")
    print(f"  - Media mapped: {len(result['id_mapping']['media'])}")


def example_3_create_with_media():
    """Example 3: Create an item with media"""
    print("\n" + "=" * 70)
    print("Example 3: Create Item with Media")
    print("=" * 70)

    api = OmekaAPI(
        base_url="https://example.com",
        key_identity="your_key_identity",
        key_credential="your_key_credential",
    )

    # Create parent item first
    item_data = {
        "o:item_set": [{"o:id": 123}],
        "dcterms:title": [
            {"type": "literal", "property_id": 1, "@value": "Parent Item"}
        ],
    }

    item_result = api.create_item(item_data, dry_run=False)

    if item_result["created"]:
        new_item_id = item_result["item_id"]
        print(f"✅ Item created with ID: {new_item_id}")

        # Create media for the item
        media_data = {
            "o:item": {"o:id": new_item_id},
            "o:ingester": "url",
            "o:source": "https://example.com/image.jpg",
            "ingest_url": "https://example.com/image.jpg",
            "dcterms:title": [
                {"type": "literal", "property_id": 1, "@value": "Image Title"}
            ],
        }

        media_result = api.create_media(media_data, dry_run=False)

        if media_result["created"]:
            print(f"✅ Media created with ID: {media_result['media_id']}")
        else:
            print(f"❌ Media creation failed: {media_result['message']}")
    else:
        print(f"❌ Item creation failed: {item_result['message']}")


def example_4_duplicate_within_instance():
    """Example 4: Duplicate an item set within same instance"""
    print("\n" + "=" * 70)
    print("Example 4: Duplicate Item Set Within Same Instance")
    print("=" * 70)

    api = OmekaAPI(
        base_url="https://example.com",
        key_identity="your_key_identity",
        key_credential="your_key_credential",
    )

    source_item_set_id = 10780
    target_item_set_id = 10781  # New empty item set

    # Download the source
    download_dir = Path("data")
    download_result = api.download_item_set(
        item_set_id=source_item_set_id,
        output_dir=download_dir,
    )

    source_dir = download_result["saved_to"]["directory"]

    # Migrate to new item set (creates copies with new IDs)
    result = api.migrate_item_set(
        source_dir=source_dir,
        target_item_set_id=target_item_set_id,
        dry_run=False,
    )

    print("Duplication complete:")
    print(f"  Original item set: {source_item_set_id}")
    print(f"  New item set: {target_item_set_id}")
    print(f"  Items duplicated: {result['items_created']}")
    print(f"  Media duplicated: {result['media_created']}")


def main():
    """Run all examples"""
    print("Migration Usage Examples")
    print("=" * 70)
    print()
    print("These examples demonstrate:")
    print("  1. Creating individual items and media")
    print("  2. Migrating complete item sets between instances")
    print("  3. Creating items with associated media")
    print("  4. Duplicating item sets within the same instance")
    print()
    print("Note: Update the base URLs and credentials before running")

    # Uncomment to run specific examples:
    # example_1_create_single_item()
    # example_2_migrate_complete_item_set()
    # example_3_create_with_media()
    # example_4_duplicate_within_instance()


if __name__ == "__main__":
    main()
