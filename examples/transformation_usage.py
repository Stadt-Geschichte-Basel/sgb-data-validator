"""Example usage of data transformation features.

This example demonstrates how to use the transformation API to:
1. Download data from an Omeka S item set
2. Apply transformations (e.g., whitespace normalization)
3. Save transformed data to files

For more details, see Issues #27 and #28:
- Issue #27: Feature: Download, Mutate, and Reupload All Data to Omeka
- Issue #28: Check for Non-Standard Whitespace Characters
"""

from src.api import OmekaAPI
from src.transformations import normalize_whitespace


def example_basic_transformation() -> None:
    """Example: Transform an item set with whitespace normalization."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Item Set Transformation")
    print("=" * 60)

    # Initialize the API (replace with your credentials)
    with OmekaAPI("https://omeka.unibe.ch") as api:
        # Download raw data first
        download = api.download_item_set(
            item_set_id=10780, output_dir="transformations"
        )
        raw_dir = download["saved_to"]["directory"]
        print(f"Downloaded raw data to: {raw_dir}")
        print(
            f"Items downloaded: {download['items_downloaded']} | "
            f"Media downloaded: {download['media_downloaded']}"
        )

        # Apply transformations to the downloaded directory
        transform = api.apply_transformations(
            input_dir=raw_dir,
            output_dir="transformations",
            apply_whitespace_normalization=True,
        )
        print(f"Items transformed: {transform['items_transformed']}")
        print(f"Media transformed: {transform['media_transformed']}")
        transformations = ", ".join(transform["transformations_applied"]) or "(none)"
        print(f"Transformations applied: {transformations}")

        if transform["saved_to"]:
            print("\nTransformed data saved to:")
            print(f"  Directory: {transform['saved_to']['directory']}")
            print(f"  Items: {transform['saved_to']['items']}")
            print(f"  Media: {transform['saved_to']['media']}")
            print(f"  Metadata: {transform['saved_to']['metadata']}")


def example_transformation_in_memory() -> None:
    """Example: Transform data in memory without saving to files."""
    print("\n" + "=" * 60)
    print("Example 2: In-Memory Transformation")
    print("=" * 60)

    with OmekaAPI("https://omeka.unibe.ch") as api:
        # For in-memory demonstration, download raw data then transform
        download = api.download_item_set(
            item_set_id=10780, output_dir="transformations"
        )
        raw_dir = download["saved_to"]["directory"]

        import json
        from pathlib import Path

        from src.transformations import transform_item_set_data

        item_set = {}
        items = json.load(open(Path(raw_dir) / "items_raw.json"))
        media = json.load(open(Path(raw_dir) / "media_raw.json"))
        if not isinstance(items, list):
            items = [items]
        if not isinstance(media, list):
            media = [media]
        _, transformed_items, transformed_media = transform_item_set_data(
            item_set, items, media
        )

        print(f"Transformed {len(transformed_items)} items in memory")
        print(f"Transformed {len(transformed_media)} media in memory")
        print(f"\nFirst item title: {transformed_items[0]['o:title']}")


def example_whitespace_normalization() -> None:
    """Example: Direct whitespace normalization."""
    print("\n" + "=" * 60)
    print("Example 3: Direct Whitespace Normalization")
    print("=" * 60)

    # Examples from Issue #28
    test_texts = [
        "Text  with  double  spaces",
        "Soft\u00adhyphen in Ger\u00adman text",
        "Non\u00a0breaking\u00a0spaces",
        "Directional\u202aformatting\u202ccharacters",
        "Multiple\n\n\n\nline breaks",
    ]

    print("\nNormalizing text examples:")
    for i, text in enumerate(test_texts, 1):
        normalized = normalize_whitespace(text)
        print(f"\n{i}. Input:  {repr(text)}")
        print(f"   Output: {repr(normalized)}")


def example_transformation_workflow() -> None:
    """Example: Complete workflow with validation."""
    print("\n" + "=" * 60)
    print("Example 4: Complete Transformation Workflow")
    print("=" * 60)

    with OmekaAPI("https://omeka.unibe.ch") as api:
        item_set_id = 10780

        print(f"Step 1: Downloading raw data from item set {item_set_id}...")
        download = api.download_item_set(
            item_set_id=item_set_id, output_dir="transformations"
        )
        raw_dir = download["saved_to"]["directory"]
        print(f"Raw directory: {raw_dir}")
        print(
            f"Items: {download['items_downloaded']} | "
            f"Media: {download['media_downloaded']}"
        )

        print("\nStep 2: Applying transformations...")
        transform = api.apply_transformations(
            input_dir=raw_dir,
            output_dir="transformations",
            apply_whitespace_normalization=True,
        )
        tx_dir = transform['saved_to']['directory']
        print(f"Step 3: Saved transformed data to: {tx_dir}")
        tx_list = transform['transformations_applied']
        print(f"Step 4: Applied transformations: {tx_list}")

        print("\nStep 4: Validating transformed data...")
        # Validate a sample of transformed items from file
        import json
        import os
        transformed_dir = transform["saved_to"]["directory"]
        items_path = os.path.join(transformed_dir, "items_transformed.json")
        items_list = json.load(open(items_path))
        sample_size = min(5, len(items_list))
        valid_count = 0
        for item in items_list[:sample_size]:
            is_valid, errors = api.validate_item(item)
            if is_valid:
                valid_count += 1

        print(
            f"  Validated {sample_size} items: {valid_count} valid, "
            f"{sample_size - valid_count} with errors"
        )

        print("\nWorkflow complete!")
        print("Next steps:")
        print("  1. Review transformed data in the output directory")
        print("  2. Verify transformations meet your requirements")
        print(
            "  3. Use the Omeka S API to upload transformed data "
            "(requires write access)"
        )


def example_http_to_https_upgrade() -> None:
    """Example: HTTP to HTTPS URL upgrade."""
    print("\n" + "=" * 60)
    print("Example 5: HTTP to HTTPS URL Upgrade")
    print("=" * 60)

    from src.transformations import apply_text_transformations, upgrade_http_to_https

    # Examples of HTTP URLs that should be upgraded
    test_texts = [
        "Visit http://www.example.com for more info",
        "Check out http://www.wikipedia.org and http://www.github.com",
        "Markdown link: [Example](http://www.example.org)",
        "Mixed: http://www.example.com and https://www.example.org",
    ]

    print("\nUpgrading HTTP to HTTPS:")
    for i, text in enumerate(test_texts, 1):
        upgraded = upgrade_http_to_https(text)
        print(f"\n{i}. Input:  {text}")
        print(f"   Output: {upgraded}")
        if "https://" in upgraded and "http://" not in upgraded.replace("https://", ""):
            print("   ✓ Successfully upgraded to HTTPS")

    # Example with comprehensive transformations
    print("\n" + "-" * 60)
    print("Comprehensive transformation (includes HTTPS upgrade):")
    complex_text = "&uuml;ber http://www.example.com d.j. text"
    result = apply_text_transformations(complex_text)
    print(f"Input:  {complex_text}")
    print(f"Output: {result}")


def example_custom_transformation() -> None:
    """Example: Custom transformation logic."""
    print("\n" + "=" * 60)
    print("Example 6: Custom Transformation Logic")
    print("=" * 60)

    from src.transformations import transform_item

    # Example item data
    item_data = {
        "o:id": 12385,
        "o:title": "Item  with  bad  whitespace",
        "dcterms:description": [
            {
                "type": "literal",
                "@value": "Description with\u00adsoft\u00adhyphens and  double  spaces",
                "property_id": 4,
            }
        ],
    }

    print("Original item:")
    print(f"  Title: {repr(item_data['o:title'])}")
    print(f"  Description: {repr(item_data['dcterms:description'][0]['@value'])}")

    # Transform the item
    transformed = transform_item(item_data)

    print("\nTransformed item:")
    print(f"  Title: {repr(transformed['o:title'])}")
    print(f"  Description: {repr(transformed['dcterms:description'][0]['@value'])}")


if __name__ == "__main__":
    print("Data Transformation Examples")
    print("=" * 60)
    print("These examples demonstrate the transformation features")
    print("implemented for Issues #27 and #28.")
    print("=" * 60)

    # Note: Some examples require network access to Omeka S
    # Uncomment the examples you want to run:

    # example_basic_transformation()
    # example_transformation_in_memory()
    example_whitespace_normalization()
    example_http_to_https_upgrade()
    example_custom_transformation()
    # example_transformation_workflow()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
