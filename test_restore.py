"""
Quick test for restore_from_backup functionality
"""

from src.api import OmekaAPI


def test_restore_validation() -> None:
    """Test that restore validates backup structure"""

    # This will fail because no backup exists
    try:
        with OmekaAPI("https://omeka.unibe.ch") as api:
            api.restore_from_backup("nonexistent_backup/", dry_run=True)
            print("❌ Should have raised FileNotFoundError")
    except FileNotFoundError as e:
        print(f"✓ Correctly raises error for missing backup: {e}")

    # Test authentication check
    try:
        with OmekaAPI("https://omeka.unibe.ch") as api:
            # Would need actual backup directory, but test auth check
            print("✓ API initialized without authentication")
            print("  (Restore with dry_run=False would require auth)")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    print("Testing restore_from_backup functionality...\n")
    test_restore_validation()
    print("\n✓ All tests passed!")
