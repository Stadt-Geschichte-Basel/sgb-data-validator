#!/usr/bin/env python3
"""Verify upload success by comparing transformed data with re-downloaded data."""

import json
import sys
from pathlib import Path
from typing import Any


def load_json(filepath: Path) -> Any:
    """Load JSON data from file."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def compare_resources(
    transformed: list[dict], downloaded: list[dict], resource_type: str
) -> dict:
    """Compare transformed data with re-downloaded data."""
    result = {
        "total": len(transformed),
        "matching": 0,
        "differences": [],
        "missing_ids": [],
    }

    # Create lookup dict by ID
    downloaded_by_id = {item.get("o:id"): item for item in downloaded}

    for trans_item in transformed:
        item_id = trans_item.get("o:id")
        if item_id not in downloaded_by_id:
            result["missing_ids"].append(item_id)
            continue

        down_item = downloaded_by_id[item_id]
        differences = []

        # Compare all fields
        for key in trans_item.keys():
            if key not in down_item:
                differences.append(f"Field {key} missing in downloaded")
                continue

            trans_val = trans_item[key]
            down_val = down_item[key]

            # Handle nested structures
            if isinstance(trans_val, list) and isinstance(down_val, list):
                if len(trans_val) != len(down_val):
                    differences.append(
                        f"{key}: length mismatch ({len(trans_val)} vs {len(down_val)})"
                    )
                    continue

                for idx, (t_entry, d_entry) in enumerate(
                    zip(trans_val, down_val, strict=False)
                ):
                    if isinstance(t_entry, dict) and isinstance(d_entry, dict):
                        for field_key in ["@value", "o:label", "o:title"]:
                            if field_key in t_entry and field_key in d_entry:
                                if t_entry[field_key] != d_entry[field_key]:
                                    differences.append(
                                        f"{key}[{idx}].{field_key}: mismatch"
                                    )

            # Handle simple values
            elif trans_val != down_val:
                # Skip fields that are expected to differ (timestamps, etc)
                if key not in ["o:modified", "@context"]:
                    differences.append(f"{key}: value mismatch")

        if differences:
            result["differences"].append(
                {
                    "id": item_id,
                    "title": trans_item.get("o:title", "Untitled")[:80],
                    "issues": differences[:5],  # First 5 issues
                    "issue_count": len(differences),
                }
            )
        else:
            result["matching"] += 1

    return result


def print_report(items_result: dict, media_result: dict) -> None:
    """Print verification report."""
    print("=" * 80)
    print("UPLOAD VERIFICATION REPORT")
    print("=" * 80)
    print()

    # Items
    print(f"ITEMS: {items_result['matching']}/{items_result['total']} match")
    if items_result["missing_ids"]:
        print(f"  Missing IDs: {items_result['missing_ids'][:10]}")
    if items_result["differences"]:
        print(f"  Resources with differences: {len(items_result['differences'])}")
        for diff in items_result["differences"][:5]:
            print(f"\n  Item {diff['id']}: {diff['title']}")
            print(f"    Issues ({diff['issue_count']}):")
            for issue in diff["issues"]:
                print(f"      - {issue}")
    print()

    # Media
    print(f"MEDIA: {media_result['matching']}/{media_result['total']} match")
    if media_result["missing_ids"]:
        print(f"  Missing IDs: {media_result['missing_ids'][:10]}")
    if media_result["differences"]:
        print(f"  Resources with differences: {len(media_result['differences'])}")
        for diff in media_result["differences"][:5]:
            print(f"\n  Media {diff['id']}: {diff['title']}")
            print(f"    Issues ({diff['issue_count']}):")
            for issue in diff["issues"]:
                print(f"      - {issue}")
    print()

    # Summary
    print("=" * 80)
    total_match = items_result["matching"] + media_result["matching"]
    total_resources = items_result["total"] + media_result["total"]
    print(f"TOTAL: {total_match}/{total_resources} resources match")

    if (
        len(items_result["differences"]) == 0
        and len(media_result["differences"]) == 0
        and len(items_result["missing_ids"]) == 0
        and len(media_result["missing_ids"]) == 0
    ):
        print("✅ Upload verified successfully! All data matches.")
    else:
        print("⚠️  Some differences detected - review details above.")
    print("=" * 80)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python verify_upload.py <transformed_dir> <downloaded_dir>")
        sys.exit(1)

    transformed_dir = Path(sys.argv[1])
    downloaded_dir = Path(sys.argv[2])

    print("Loading data...")
    trans_items = load_json(transformed_dir / "items_transformed.json")
    down_items = load_json(downloaded_dir / "items_raw.json")
    trans_media = load_json(transformed_dir / "media_transformed.json")
    down_media = load_json(downloaded_dir / "media_raw.json")

    print("Comparing data...")
    items_result = compare_resources(trans_items, down_items, "items")
    media_result = compare_resources(trans_media, down_media, "media")

    print_report(items_result, media_result)


if __name__ == "__main__":
    main()
