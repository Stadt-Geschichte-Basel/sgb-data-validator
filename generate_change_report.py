#!/usr/bin/env python3
"""Generate a detailed report of all changed items and media."""

import itertools
import json
import sys
from pathlib import Path
from typing import Any


def load_json(filepath: Path) -> Any:
    """Load JSON data from file."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def find_changed_resources(
    raw_data: list[dict], transformed_data: list[dict]
) -> list[dict]:
    """Find all resources that were changed during transformation."""
    changed = []

    for raw_item, trans_item in itertools.zip_longest(raw_data, transformed_data):
        # Handle missing resources
        if raw_item is None and trans_item is not None:
            # Resource added
            resource_id = trans_item.get("o:id", "unknown")
            title = trans_item.get("o:title", "Untitled")
            changed.append(
                {
                    "id": resource_id,
                    "title": title[:80] if len(title) > 80 else title,
                    "changes": [
                        {
                            "field": "RESOURCE_ADDED",
                            "before_length": 0,
                            "after_length": len(str(trans_item)),
                            "chars_removed": -len(str(trans_item)),
                        }
                    ],
                    "total_changes": 1,
                    "total_chars_removed": -len(str(trans_item)),
                }
            )
            continue

        if trans_item is None and raw_item is not None:
            # Resource removed
            resource_id = raw_item.get("o:id", "unknown")
            title = raw_item.get("o:title", "Untitled")
            changed.append(
                {
                    "id": resource_id,
                    "title": title[:80] if len(title) > 80 else title,
                    "changes": [
                        {
                            "field": "RESOURCE_REMOVED",
                            "before_length": len(str(raw_item)),
                            "after_length": 0,
                            "chars_removed": len(str(raw_item)),
                        }
                    ],
                    "total_changes": 1,
                    "total_chars_removed": len(str(raw_item)),
                }
            )
            continue

        if raw_item is None or trans_item is None:
            continue

        resource_id = raw_item.get("o:id", "unknown")
        title = trans_item.get("o:title", "Untitled")
        changes_in_resource = []

        # Compare all fields
        for key in raw_item.keys():
            if key not in trans_item:
                continue

            raw_val = raw_item[key]
            trans_val = trans_item[key]

            # Handle nested structures (like dcterms fields)
            if isinstance(raw_val, list) and isinstance(trans_val, list):
                for idx, (raw_entry, trans_entry) in enumerate(
                    itertools.zip_longest(raw_val, trans_val)
                ):
                    # Handle missing entries
                    if raw_entry is None and trans_entry is not None:
                        changes_in_resource.append(
                            {
                                "field": f"{key}[{idx}].ADDED",
                                "before_length": 0,
                                "after_length": len(str(trans_entry)),
                                "chars_removed": -len(str(trans_entry)),
                            }
                        )
                        continue

                    if trans_entry is None and raw_entry is not None:
                        changes_in_resource.append(
                            {
                                "field": f"{key}[{idx}].REMOVED",
                                "before_length": len(str(raw_entry)),
                                "after_length": 0,
                                "chars_removed": len(str(raw_entry)),
                            }
                        )
                        continue

                    if raw_entry is None or trans_entry is None:
                        continue

                    if isinstance(raw_entry, dict) and isinstance(trans_entry, dict):
                        for field_key in ["@value", "o:label"]:
                            if field_key in raw_entry and field_key in trans_entry:
                                raw_text = raw_entry[field_key]
                                trans_text = trans_entry[field_key]
                                if raw_text != trans_text:
                                    changes_in_resource.append(
                                        {
                                            "field": f"{key}[{idx}].{field_key}",
                                            "before_length": len(str(raw_text)),
                                            "after_length": len(str(trans_text)),
                                            "chars_removed": len(str(raw_text))
                                            - len(str(trans_text)),
                                        }
                                    )

            # Handle simple string fields
            elif isinstance(raw_val, str) and isinstance(trans_val, str):
                if raw_val != trans_val:
                    changes_in_resource.append(
                        {
                            "field": key,
                            "before_length": len(raw_val),
                            "after_length": len(trans_val),
                            "chars_removed": len(raw_val) - len(trans_val),
                        }
                    )

        if changes_in_resource:
            changed.append(
                {
                    "id": resource_id,
                    "title": title[:80] if len(title) > 80 else title,
                    "changes": changes_in_resource,
                    "total_changes": len(changes_in_resource),
                    "total_chars_removed": sum(
                        c["chars_removed"] for c in changes_in_resource
                    ),
                }
            )

    return changed


def print_report(
    items_changed: list[dict],
    media_changed: list[dict],
    output_file: str,
    total_items: int,
    total_media: int,
) -> None:
    """Print and save a detailed report of all changes."""
    lines = []
    lines.append("=" * 100)
    lines.append("COMPLETE TRANSFORMATION CHANGE REPORT")
    lines.append("=" * 100)
    lines.append("")

    # Items section
    lines.append(f"ITEMS CHANGED: {len(items_changed)} out of {total_items}")
    lines.append("=" * 100)
    lines.append("")

    for item in items_changed:
        lines.append(
            f"Item ID: {item['id']} | Title: {item['title']} | Changes: {item['total_changes']} | Chars removed: {item['total_chars_removed']}"
        )
        lines.append(f"  URL: https://omeka.unibe.ch/admin/item/{item['id']}")
        for change in item["changes"]:
            lines.append(
                f"    - {change['field']}: {change['before_length']} → {change['after_length']} chars ({change['chars_removed']:+d})"
            )
        lines.append("")

    # Media section
    lines.append("")
    lines.append(f"MEDIA CHANGED: {len(media_changed)} out of {total_media}")
    lines.append("=" * 100)
    lines.append("")

    for media in media_changed:
        lines.append(
            f"Media ID: {media['id']} | Title: {media['title']} | Changes: {media['total_changes']} | Chars removed: {media['total_chars_removed']}"
        )
        lines.append(f"  URL: https://omeka.unibe.ch/admin/media/{media['id']}")
        for change in media["changes"]:
            lines.append(
                f"    - {change['field']}: {change['before_length']} → {change['after_length']} chars ({change['chars_removed']:+d})"
            )
        lines.append("")

    # Summary
    lines.append("")
    lines.append("=" * 100)
    lines.append("SUMMARY")
    lines.append("=" * 100)
    lines.append(f"Total items changed: {len(items_changed)}")
    lines.append(f"Total media changed: {len(media_changed)}")
    lines.append(f"Total resources changed: {len(items_changed) + len(media_changed)}")
    total_chars = sum(i["total_chars_removed"] for i in items_changed) + sum(
        m["total_chars_removed"] for m in media_changed
    )
    lines.append(f"Total characters removed: {total_chars}")
    lines.append("=" * 100)

    # Print to console
    report = "\n".join(lines)
    print(report)

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n✓ Report saved to: {output_file}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python generate_change_report.py <raw_dir> <transformed_dir>")
        sys.exit(1)

    raw_dir = Path(sys.argv[1])
    transformed_dir = Path(sys.argv[2])
    output_file = "transformation_changes_detailed.txt"

    # Load data
    print("Loading data...")
    raw_items = load_json(raw_dir / "items_raw.json")
    transformed_items = load_json(transformed_dir / "items_transformed.json")
    raw_media = load_json(raw_dir / "media_raw.json")
    transformed_media = load_json(transformed_dir / "media_transformed.json")

    # Find changed resources
    print("Analyzing changes...")
    items_changed = find_changed_resources(raw_items, transformed_items)
    media_changed = find_changed_resources(raw_media, transformed_media)

    # Print report
    print_report(
        items_changed,
        media_changed,
        output_file,
        total_items=len(raw_items),
        total_media=len(raw_media),
    )


if __name__ == "__main__":
    main()
