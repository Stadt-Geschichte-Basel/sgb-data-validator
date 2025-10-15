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
    with OmekaAPI(
        "https://omeka.unibe.ch",
        # Optional: Add API credentials for private resources
        # key_identity="YOUR_KEY_IDENTITY",
        # key_credential="YOUR_KEY_CREDENTIAL",
    ) as api:
        # Transform an item set and save to files
        result = api.transform_item_set(
            item_set_id=10780,
            output_dir="transformations",
            apply_whitespace_normalization=True,
        )

        print(f"Item Set ID: {result['item_set_id']}")
        print(f"Items transformed: {result['items_transformed']}")
        print(f"Media transformed: {result['media_transformed']}")
        transformations = ", ".join(result["transformations_applied"])
        print(f"Transformations applied: {transformations}")

        if result["saved_to"]:
            print("\nTransformed data saved to:")
            print(f"  Directory: {result['saved_to']['directory']}")
            print(f"  Items: {result['saved_to']['items']}")
            print(f"  Media: {result['saved_to']['media']}")
            print(f"  Metadata: {result['saved_to']['metadata']}")


def example_transformation_in_memory() -> None:
    """Example: Transform data in memory without saving to files."""
    print("\n" + "=" * 60)
    print("Example 2: In-Memory Transformation")
    print("=" * 60)

    with OmekaAPI("https://omeka.unibe.ch") as api:
        # Transform without saving to files
        result = api.transform_item_set(
            item_set_id=10780,
            output_dir=None,  # Don't save to files
            apply_whitespace_normalization=True,
        )

        print(f"Transformed {result['items_transformed']} items in memory")
        print(f"Transformed {result['media_transformed']} media in memory")

        # Access transformed data directly
        transformed_items = result["items"]
        transformed_media = result["media"]

        print(f"\nFirst item title: {transformed_items[0]['o:title']}")
        print(f"First media title: {transformed_media[0]['o:title']}")


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

        print(f"Step 1: Downloading data from item set {item_set_id}...")
        # Transform and save
        result = api.transform_item_set(
            item_set_id=item_set_id,
            output_dir="transformations",
            apply_whitespace_normalization=True,
        )

        print(f"Step 2: Applied transformations: {result['transformations_applied']}")
        print(f"Step 3: Saved transformed data to: {result['saved_to']['directory']}")

        print("\nStep 4: Validating transformed data...")
        # Validate a sample of transformed items
        sample_size = min(5, len(result["items"]))
        valid_count = 0
        for item in result["items"][:sample_size]:
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


def example_custom_transformation() -> None:
    """Example: Custom transformation logic."""
    print("\n" + "=" * 60)
    print("Example 5: Custom Transformation Logic")
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
    example_custom_transformation()
    # example_transformation_workflow()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
