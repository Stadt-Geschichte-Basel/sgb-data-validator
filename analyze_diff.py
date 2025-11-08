#!/usr/bin/env python3
"""Analyze differences between raw and transformed data."""

import json
import sys
from pathlib import Path
from typing import Any


def load_json(filepath: Path) -> Any:
    """Load JSON data from file."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def find_differences(raw_data: list[dict], transformed_data: list[dict]) -> dict:
    """Find differences between raw and transformed data."""
    changes = {
        "total_resources": len(raw_data),
        "fields_changed": 0,
        "changes_by_field": {},
        "examples": [],
    }

    for raw_item, trans_item in zip(raw_data, transformed_data, strict=True):
        resource_id = raw_item.get("o:id", "unknown")

        # Compare all fields
        for key in raw_item.keys():
            if key not in trans_item:
                continue

            raw_val = raw_item[key]
            trans_val = trans_item[key]

            # Handle nested structures (like dcterms fields)
            if isinstance(raw_val, list) and isinstance(trans_val, list):
                for raw_entry, trans_entry in zip(raw_val, trans_val, strict=True):
                    if isinstance(raw_entry, dict) and isinstance(trans_entry, dict):
                        for field_key in ["@value", "o:label"]:
                            if field_key in raw_entry and field_key in trans_entry:
                                raw_text = raw_entry[field_key]
                                trans_text = trans_entry[field_key]
                                if raw_text != trans_text:
                                    changes["fields_changed"] += 1
                                    field_name = f"{key}.{field_key}"
                                    changes["changes_by_field"][field_name] = (
                                        changes["changes_by_field"].get(field_name, 0)
                                        + 1
                                    )

                                    # Save first 5 examples per field
                                    field_examples = [
                                        e
                                        for e in changes["examples"]
                                        if e["field"] == field_name
                                    ]
                                    if len(field_examples) < 5:
                                        changes["examples"].append(
                                            {
                                                "resource_id": resource_id,
                                                "field": field_name,
                                                "before": raw_text,
                                                "after": trans_text,
                                                "diff_chars": len(raw_text)
                                                - len(trans_text),
                                            }
                                        )

            # Handle simple string fields
            elif isinstance(raw_val, str) and isinstance(trans_val, str):
                if raw_val != trans_val:
                    changes["fields_changed"] += 1
                    changes["changes_by_field"][key] = (
                        changes["changes_by_field"].get(key, 0) + 1
                    )

                    field_examples = [
                        e for e in changes["examples"] if e["field"] == key
                    ]
                    if len(field_examples) < 5:
                        changes["examples"].append(
                            {
                                "resource_id": resource_id,
                                "field": key,
                                "before": raw_val,
                                "after": trans_val,
                                "diff_chars": len(raw_val) - len(trans_val),
                            }
                        )

    return changes


def print_report(items_changes: dict, media_changes: dict) -> None:
    """Print a formatted report of changes."""
    print("=" * 80)
    print("TRANSFORMATION ANALYSIS REPORT")
    print("=" * 80)
    print()

    # Items summary
    print("ITEMS:")
    print(f"  Total items: {items_changes['total_resources']}")
    print(f"  Fields changed: {items_changes['fields_changed']}")
    print()

    if items_changes["changes_by_field"]:
        print("  Changes by field:")
        for field, count in sorted(
            items_changes["changes_by_field"].items(), key=lambda x: -x[1]
        ):
            print(f"    {field}: {count}")
        print()

    if items_changes["examples"]:
        print("  Example changes (first 5 per field):")
        for ex in items_changes["examples"][:10]:
            print(f"\n    Item {ex['resource_id']} - {ex['field']}:")
            print(f"      BEFORE ({len(ex['before'])} chars): {ex['before'][:100]!r}")
            print(f"      AFTER  ({len(ex['after'])} chars): {ex['after'][:100]!r}")
            print(f"      Difference: {ex['diff_chars']} chars removed")
        print()

    # Media summary
    print("MEDIA:")
    print(f"  Total media: {media_changes['total_resources']}")
    print(f"  Fields changed: {media_changes['fields_changed']}")
    print()

    if media_changes["changes_by_field"]:
        print("  Changes by field:")
        for field, count in sorted(
            media_changes["changes_by_field"].items(), key=lambda x: -x[1]
        ):
            print(f"    {field}: {count}")
        print()

    if media_changes["examples"]:
        print("  Example changes (first 5):")
        for ex in media_changes["examples"][:5]:
            print(f"\n    Media {ex['resource_id']} - {ex['field']}:")
            print(f"      BEFORE ({len(ex['before'])} chars): {ex['before'][:100]!r}")
            print(f"      AFTER  ({len(ex['after'])} chars): {ex['after'][:100]!r}")
            print(f"      Difference: {ex['diff_chars']} chars removed")
        print()

    # Summary
    total_changes = items_changes["fields_changed"] + media_changes["fields_changed"]
    print("=" * 80)
    print(f"TOTAL FIELD CHANGES: {total_changes}")
    print("=" * 80)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python analyze_diff.py <raw_dir> <transformed_dir>")
        sys.exit(1)

    raw_dir = Path(sys.argv[1])
    transformed_dir = Path(sys.argv[2])

    # Load data
    print("Loading data...")
    raw_items = load_json(raw_dir / "items_raw.json")
    transformed_items = load_json(transformed_dir / "items_transformed.json")
    raw_media = load_json(raw_dir / "media_raw.json")
    transformed_media = load_json(transformed_dir / "media_transformed.json")

    # Analyze differences
    print("Analyzing differences...")
    items_changes = find_differences(raw_items, transformed_items)
    media_changes = find_differences(raw_media, transformed_media)

    # Print report
    print_report(items_changes, media_changes)


if __name__ == "__main__":
    main()
