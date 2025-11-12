# Migration and Creation Methods

This document explains how to use the creation methods added to support true data migration between Omeka S instances.

## Overview

The creation methods enable you to:

- **Create new items and media** with new IDs (not just update existing ones)
- **Migrate complete item sets** between different Omeka S instances
- **Duplicate item sets** within the same instance
- **Automatic ID mapping** so media references point to the correct new item IDs

## Methods

### `create_item(data, dry_run=True)`

Create a new item in Omeka S. The server assigns a new ID.

```python
from src.api import OmekaAPI

with OmekaAPI(
    "https://target.example.com",
    key_identity="your_key",
    key_credential="your_secret"
) as api:
    item_data = {
        "o:item_set": [{"o:id": 123}],
        "dcterms:title": [
            {"type": "literal", "property_id": 1, "@value": "New Item"}
        ],
    }

    # Validate first
    result = api.create_item(item_data, dry_run=True)

    # Create for real
    if result["validation_passed"]:
        result = api.create_item(item_data, dry_run=False)
        print(f"Created item {result['item_id']}")
```

**Key points:**

- Do NOT include `o:id` in the data (it will be assigned by the server)
- Validation is basic - the server performs full validation
- Returns the new `item_id` on success

### `create_media(data, dry_run=True)`

Create a new media resource associated with an existing item.

```python
media_data = {
    "o:item": {"o:id": 121200},  # Must reference existing item
    "o:ingester": "url",
    "o:source": "https://example.com/image.jpg",
    "ingest_url": "https://example.com/image.jpg",
}

result = api.create_media(media_data, dry_run=False)
if result["created"]:
    print(f"Created media {result['media_id']}")
```

**Key points:**

- Must include `o:item` reference to parent item
- Must include `o:ingester` (typically "url" or "upload")
- Returns the new `media_id` on success

### `migrate_item_set(source_dir, target_item_set_id, dry_run=True)`

Migrate a complete item set to a new instance or item set.

```python
# Download from source instance
source_api = OmekaAPI("https://source.example.com")
download_result = source_api.download_item_set(10780, "data/")
source_dir = download_result["saved_to"]["directory"]

# Apply transformations if needed
transformed_dir = source_api.apply_transformations(source_dir)

# Migrate to target instance
target_api = OmekaAPI(
    "https://target.example.com",
    key_identity="your_key",
    key_credential="your_secret"
)

# Validate first
result = target_api.migrate_item_set(
    source_dir=transformed_dir,
    target_item_set_id=456,
    dry_run=True
)

# Perform migration
if len(result["errors"]) == 0:
    result = target_api.migrate_item_set(
        source_dir=transformed_dir,
        target_item_set_id=456,
        dry_run=False
    )
    print(f"Migrated {result['items_created']} items")
    print(f"ID mapping: {result['id_mapping']['items']}")
```

**Key points:**

- Reads `items.json` and `media.json` from source directory
- Creates items first, then media with updated references
- Returns ID mapping from old IDs to new IDs
- Automatically updates `o:item_set` and `o:item` references

## Migration Workflows

### Cross-Instance Migration

Migrate data from one Omeka S instance to another:

```python
# 1. Download from source
source_api = OmekaAPI("https://source.example.com")
download_result = source_api.download_item_set(10780, "data/")

# 2. Transform data
transformed_dir = source_api.apply_transformations(
    download_result["saved_to"]["directory"]
)

# 3. Migrate to target
target_api = OmekaAPI("https://target.example.com", key_identity="...", key_credential="...")
result = target_api.migrate_item_set(transformed_dir, target_item_set_id=456, dry_run=False)
```

### Within-Instance Duplication

Create a duplicate of an item set in the same instance:

```python
api = OmekaAPI("https://example.com", key_identity="...", key_credential="...")

# Download source item set
download_result = api.download_item_set(10780, "data/")

# Migrate to new item set (creates copies)
result = api.migrate_item_set(
    source_dir=download_result["saved_to"]["directory"],
    target_item_set_id=10781,  # New empty item set
    dry_run=False
)
```

## ID Mapping

The `migrate_item_set()` method returns an ID mapping that tracks old IDs to new IDs:

```python
result = api.migrate_item_set(source_dir, target_item_set_id, dry_run=False)

# Access ID mappings
old_to_new_items = result["id_mapping"]["items"]
old_to_new_media = result["id_mapping"]["media"]

# Example: {123: 456, 124: 457, ...}
print(f"Old item 123 is now item {old_to_new_items[123]}")
```

This is useful for:

- Updating external references to items
- Tracking which resources were migrated
- Debugging migration issues

## Validation

All creation methods support dry-run validation:

```python
# Always validate first
result = api.create_item(item_data, dry_run=True)

if result["validation_passed"]:
    # Safe to proceed
    result = api.create_item(item_data, dry_run=False)
else:
    # Fix errors
    print(f"Validation errors: {result['errors']}")
```

**Note:** Dry-run validation is basic (checks required fields). The server performs full validation when actually creating resources.

## Error Handling

Creation methods return detailed error information:

```python
result = api.migrate_item_set(source_dir, target_item_set_id, dry_run=False)

print(f"Items processed: {result['items_processed']}")
print(f"Items created: {result['items_created']}")
print(f"Items failed: {result['items_failed']}")

if result["errors"]:
    for error in result["errors"]:
        print(f"Error: {error}")
```

## Examples

See `examples/migration_usage.py` for complete working examples:

1. Creating individual items and media
2. Migrating complete item sets between instances
3. Creating items with associated media
4. Duplicating item sets within the same instance

## Comparison: Update vs Create

| Feature            | Update Methods            | Creation Methods       |
| ------------------ | ------------------------- | ---------------------- |
| **Use case**       | Modify existing resources | Create new resources   |
| **IDs**            | Must exist in target      | Assigned by server     |
| **Migration**      | Requires matching IDs     | Works across instances |
| **Duplication**    | Not supported             | Supported              |
| **Authentication** | Required                  | Required               |
| **Dry-run**        | Validates with full model | Basic validation       |

## See Also

- `API.md` - Complete API documentation with workflow diagrams
- `examples/migration_usage.py` - Working code examples
- `test/test_creation.py` - Test cases showing expected behavior
