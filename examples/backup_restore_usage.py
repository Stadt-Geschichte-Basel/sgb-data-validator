"""
Example: Backup and Restore Operations

This example demonstrates how to:
1. Create a backup of an item set
2. Validate a backup
3. Restore data from a backup
"""

from src.api import OmekaAPI


def example_backup() -> None:
    """Create a backup of an item set"""
    print("=" * 80)
    print("EXAMPLE: CREATE BACKUP")
    print("=" * 80)

    # Create backup (no authentication required for public data)
    with OmekaAPI("https://omeka.unibe.ch") as api:
        print("Creating backup of item set 10780...")
        backup_paths = api.backup_item_set(10780, "backups/")

        print("\n✓ Backup created successfully!")
        print(f"  Manifest: {backup_paths['manifest']}")
        print(f"  Items: {backup_paths['items']}")
        print(f"  Media: {backup_paths['media']}")
        print(f"\nBackup directory: {backup_paths['manifest'].parent}")


def example_validate_backup() -> None:
    """Validate a backup without restoring"""
    print("\n" + "=" * 80)
    print("EXAMPLE: VALIDATE BACKUP")
    print("=" * 80)

    # Note: Replace with actual backup directory
    backup_dir = "backups/itemset_10780_20251112_103000"

    try:
        with OmekaAPI("https://omeka.unibe.ch") as api:
            print(f"Validating backup: {backup_dir}")
            result = api.restore_from_backup(backup_dir, dry_run=True)

            print("\n✓ Backup validated successfully!")
            print(f"  Item set ID: {result['item_set_id']}")
            print(f"  Items to restore: {result['items_count']}")
            print(f"  Media to restore: {result['media_count']}")
            print(f"\n{result['message']}")
    except FileNotFoundError as e:
        print(f"\n✗ Backup not found: {e}")
        print("  Create a backup first using example_backup()")


def example_restore_backup() -> None:
    """Restore data from a backup"""
    print("\n" + "=" * 80)
    print("EXAMPLE: RESTORE FROM BACKUP")
    print("=" * 80)

    # Note: Replace with actual backup directory and credentials
    backup_dir = "backups/itemset_10780_20251112_103000"
    key_identity = "YOUR_KEY_IDENTITY"
    key_credential = "YOUR_KEY_CREDENTIAL"

    print("⚠️  IMPORTANT: This example requires:")
    print("  1. A valid backup directory")
    print("  2. API credentials (key_identity and key_credential)")
    print("  3. Resources must already exist in target instance")
    print()

    # Uncomment and configure to run:
    """
    try:
        with OmekaAPI(
            "https://omeka.unibe.ch",
            key_identity=key_identity,
            key_credential=key_credential
        ) as api:
            print(f"Restoring from: {backup_dir}")
            
            # Dry run first
            print("Step 1: Dry run validation...")
            dry_result = api.restore_from_backup(backup_dir, dry_run=True)
            print(f"  {dry_result['message']}")
            
            # Confirm before proceeding
            response = input("\\nProceed with actual restore? (y/n): ")
            if response.lower() != 'y':
                print("Restore cancelled")
                return
            
            # Actual restore
            print("\\nStep 2: Restoring data...")
            result = api.restore_from_backup(backup_dir, dry_run=False)
            
            print(f"\\n{result['message']}")
            print(f"  Items restored: {result['items_restored']}/{result['items_processed']}")
            print(f"  Media restored: {result['media_restored']}/{result['media_processed']}")
            
            if result["errors"]:
                print(f"\\n⚠ Errors occurred:")
                for error in result["errors"][:5]:
                    print(f"  - {error['type']} {error.get('item_id', error.get('media_id', ''))}: {error['message']}")
                if len(result["errors"]) > 5:
                    print(f"  ... and {len(result['errors']) - 5} more errors")
            else:
                print("\\n✓ Restore completed without errors!")
                
    except ValueError as e:
        print(f"\\n✗ Configuration error: {e}")
    except FileNotFoundError as e:
        print(f"\\n✗ Backup not found: {e}")
    except Exception as e:
        print(f"\\n✗ Unexpected error: {e}")
    """

    print("Uncomment the code above and configure to run this example.")


def example_backup_workflow() -> None:
    """Complete backup and restore workflow"""
    print("\n" + "=" * 80)
    print("COMPLETE WORKFLOW: BACKUP → VALIDATE → RESTORE")
    print("=" * 80)

    print("""
This workflow demonstrates:
1. Creating a backup of an item set
2. Validating the backup structure
3. Restoring data to the same or different instance

Steps:
------

# 1. Create backup (no auth required for public data)
with OmekaAPI("https://omeka.unibe.ch") as api:
    backup = api.backup_item_set(10780, "backups/")
    backup_dir = backup["manifest"].parent

# 2. Validate backup (dry run)
with OmekaAPI("https://omeka.unibe.ch") as api:
    result = api.restore_from_backup(backup_dir, dry_run=True)
    print(result["message"])

# 3. Restore to same or different instance (requires auth)
with OmekaAPI(
    "https://omeka.unibe.ch",  # or different target instance
    key_identity="YOUR_KEY",
    key_credential="YOUR_SECRET"
) as api:
    result = api.restore_from_backup(backup_dir, dry_run=False)
    print(f"Restored {result['items_restored']} items")

Use Cases:
----------
- Regular backups for disaster recovery
- Testing changes in development before production
- Migrating data between Omeka instances (same IDs required)
- Rolling back unwanted changes
- Syncing data across environments
    """)


if __name__ == "__main__":
    print("Backup and Restore Examples")
    print("=" * 80)
    print()
    print("Available examples:")
    print("1. example_backup() - Create a backup")
    print("2. example_validate_backup() - Validate a backup")
    print("3. example_restore_backup() - Restore from backup")
    print("4. example_backup_workflow() - Complete workflow overview")
    print()

    # Run examples
    # Uncomment to run individual examples:

    # example_backup()
    # example_validate_backup()
    # example_restore_backup()
    example_backup_workflow()

    print("\n" + "=" * 80)
    print("For more information, see API.md documentation")
    print("=" * 80)
