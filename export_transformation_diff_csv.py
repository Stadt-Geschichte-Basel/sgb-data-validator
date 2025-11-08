#!/usr/bin/env python3
"""Export detailed transformation differences to a CSV file.

Generates a CSV with one row per changed textual field.
Columns:
    resource_type  Item or Media
    resource_id    Omeka o:id
    field          Field name (with index for list entries)
    original       Original (raw) text value
    transformed    Transformed text value
    diff           A compact inline diff (unified style, truncated)

Usage:
    uv run python export_transformation_diff_csv.py \
        <raw_dir> <transformed_dir> [output.csv]

Example:
    uv run python export_transformation_diff_csv.py \
        data/raw_itemset_10780_20251108_185258/ \
        data/transformed_itemset_10780_20251108_185311/ \
        transformation_diff.csv
"""

from __future__ import annotations

import csv
import difflib
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unified_inline_diff(a: str, b: str, max_len: int = 300) -> str:
    """Return a compact unified diff between a and b.

    Truncates very long outputs for readability.
    """
    if a == b:
        return ""
    diff_lines = list(
        difflib.unified_diff(
            a.splitlines(keepends=True), b.splitlines(keepends=True), lineterm=""
        )
    )
    joined = "".join(diff_lines)
    if len(joined) > max_len:
        return joined[:max_len] + "... (truncated)"
    return joined


def iter_text_changes(
    raw_obj: dict[str, Any],
    trans_obj: dict[str, Any],
    resource_type: str,
) -> Iterable[dict[str, str]]:
    """Yield change records for textual fields between raw_obj and trans_obj."""
    resource_id = raw_obj.get("o:id") or trans_obj.get("o:id") or "unknown"

    for key, raw_val in raw_obj.items():
        if key not in trans_obj:
            continue
        trans_val = trans_obj[key]

        # Simple string field
        if (
            isinstance(raw_val, str)
            and isinstance(trans_val, str)
            and raw_val != trans_val
        ):
            yield {
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "field": key,
                "original": raw_val,
                "transformed": trans_val,
                "diff": unified_inline_diff(raw_val, trans_val),
            }
            continue

        # List of property dicts (e.g. dcterms:*)
        if isinstance(raw_val, list) and isinstance(trans_val, list):
            max_len = max(len(raw_val), len(trans_val))
            for idx in range(max_len):
                try:
                    r_entry = raw_val[idx]
                except IndexError:
                    r_entry = None
                try:
                    t_entry = trans_val[idx]
                except IndexError:
                    t_entry = None

                if r_entry is None and t_entry is None:
                    continue
                # Handle added / removed entries
                if r_entry is None and t_entry is not None:
                    # Only include if textual content present
                    if isinstance(t_entry, dict):
                        txt = t_entry.get("@value") or t_entry.get("o:label")
                        if isinstance(txt, str):
                            yield {
                                "resource_type": resource_type,
                                "resource_id": str(resource_id),
                                "field": f"{key}[{idx}] (added)",
                                "original": "",
                                "transformed": txt,
                                "diff": unified_inline_diff("", txt),
                            }
                    continue
                if t_entry is None and r_entry is not None:
                    if isinstance(r_entry, dict):
                        txt = r_entry.get("@value") or r_entry.get("o:label")
                        if isinstance(txt, str):
                            yield {
                                "resource_type": resource_type,
                                "resource_id": str(resource_id),
                                "field": f"{key}[{idx}] (removed)",
                                "original": txt,
                                "transformed": "",
                                "diff": unified_inline_diff(txt, ""),
                            }
                    continue

                # Compare dict entries
                if isinstance(r_entry, dict) and isinstance(t_entry, dict):
                    for sub_key in ("@value", "o:label"):
                        if sub_key in r_entry and sub_key in t_entry:
                            r_text = r_entry.get(sub_key)
                            t_text = t_entry.get(sub_key)
                            if (
                                isinstance(r_text, str)
                                and isinstance(t_text, str)
                                and r_text != t_text
                            ):
                                yield {
                                    "resource_type": resource_type,
                                    "resource_id": str(resource_id),
                                    "field": f"{key}[{idx}].{sub_key}",
                                    "original": r_text,
                                    "transformed": t_text,
                                    "diff": unified_inline_diff(r_text, t_text),
                                }


def build_index(data: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {d.get("o:id"): d for d in data if isinstance(d, dict) and "o:id" in d}


def collect_changes(
    raw_list: list[dict[str, Any]],
    trans_list: list[dict[str, Any]],
    resource_type: str,
) -> list[dict[str, str]]:
    raw_index = build_index(raw_list)
    trans_index = build_index(trans_list)
    all_ids = sorted(set(raw_index.keys()) | set(trans_index.keys()))
    rows: list[dict[str, str]] = []
    for rid in all_ids:
        raw_obj = raw_index.get(rid, {})
        trans_obj = trans_index.get(rid, {})
        if not raw_obj or not trans_obj:
            # Added / removed whole resource – we only record textual fields
            # If added, iterate its textual fields as additions
            if trans_obj and not raw_obj:
                for key, val in trans_obj.items():
                    if isinstance(val, str) and val.strip():
                        rows.append(
                            {
                                "resource_type": resource_type,
                                "resource_id": str(rid),
                                "field": f"{key} (added resource)",
                                "original": "",
                                "transformed": val,
                                "diff": unified_inline_diff("", val),
                            }
                        )
                continue
            if raw_obj and not trans_obj:
                for key, val in raw_obj.items():
                    if isinstance(val, str) and val.strip():
                        rows.append(
                            {
                                "resource_type": resource_type,
                                "resource_id": str(rid),
                                "field": f"{key} (removed resource)",
                                "original": val,
                                "transformed": "",
                                "diff": unified_inline_diff(val, ""),
                            }
                        )
                continue
        # Standard comparison
        for change in iter_text_changes(raw_obj, trans_obj, resource_type):
            rows.append(change)
    return rows


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "resource_type",
        "resource_id",
        "field",
        "original",
        "transformed",
        "diff",
    ]
    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(
            "Usage: python export_transformation_diff_csv.py "
            "<raw_dir> <transformed_dir> [output.csv]"
        )
        return 1

    raw_dir = Path(sys.argv[1])
    trans_dir = Path(sys.argv[2])
    output = (
        Path(sys.argv[3]) if len(sys.argv) == 4 else Path("transformation_diff.csv")
    )

    # Load data
    raw_items = load_json(raw_dir / "items_raw.json")
    trans_items = load_json(trans_dir / "items_transformed.json")
    raw_media = load_json(raw_dir / "media_raw.json")
    trans_media = load_json(trans_dir / "media_transformed.json")

    if not isinstance(raw_items, list):
        raw_items = [raw_items]
    if not isinstance(trans_items, list):
        trans_items = [trans_items]
    if not isinstance(raw_media, list):
        raw_media = [raw_media]
    if not isinstance(trans_media, list):
        trans_media = [trans_media]

    # Collect changes
    item_rows = collect_changes(raw_items, trans_items, "Item")
    media_rows = collect_changes(raw_media, trans_media, "Media")
    all_rows = item_rows + media_rows

    write_csv(all_rows, output)

    print(f"✓ Diff CSV written: {output} ({len(all_rows)} changed rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
