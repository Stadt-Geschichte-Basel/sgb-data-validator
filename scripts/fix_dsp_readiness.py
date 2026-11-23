"""Apply reviewed value edits that the DSP upload needs.

The edit list is a JSON file with one entry per field:

    {"edits": [{"kind": "media", "id": 13654, "field": "dcterms:source",
                "old": [{"type": "uri", "@id": "...", "o:label": "..."}],
                "new": [{"type": "literal", "@value": "Keystone, 119619131 (RM)"}],
                "why": "B5"}]}

"old" must match the live values exactly (type, @value, @id, o:label), in order.
"new" replaces all values of the field. An empty "new" list removes the field.
The script previews by default. --apply --exclusive-write writes, keeps a
before-edit copy, and reads every record back.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sgb_validator.api import Omeka, OmekaError
from sgb_validator.writes import require_exclusive_write, update_record

ROOT = Path(__file__).resolve().parent.parent

#: Omeka property IDs of the Dublin Core terms this script may edit.
PROPERTIES = {
    "dcterms:creator": (2, "Creator"),
    "dcterms:publisher": (5, "Publisher"),
    "dcterms:type": (8, "Type"),
    "dcterms:identifier": (10, "Identifier"),
    "dcterms:source": (11, "Source"),
    "dcterms:language": (12, "Language"),
    "dcterms:relation": (13, "Relation"),
    "dcterms:isPartOf": (33, "Is Part Of"),
    "dcterms:temporal": (41, "Temporal Coverage"),
    "dcterms:license": (49, "License"),
}
KEYS = ("type", "@value", "@id", "o:label")


def shape(value: dict[str, Any]) -> dict[str, Any]:
    """The part of a value that an edit compares."""
    return {key: value[key] for key in KEYS if value.get(key) not in (None, "")}


def native(field: str, value: dict[str, Any], like: dict[str, Any]) -> dict[str, Any]:
    """A complete Omeka value. Keep property and visibility of the old value."""
    pid, label = PROPERTIES[field]
    return {
        "property_id": like.get("property_id", pid),
        "property_label": like.get("property_label", label),
        "is_public": like.get("is_public", True),
        **value,
    }


def plan_record(before: dict[str, Any], edits: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the new record. Raise ValueError when a live value differs."""
    after = dict(before)
    for edit in edits:
        field = edit["field"]
        if field not in PROPERTIES:
            raise ValueError(f"{field} is not allowed")
        live = before.get(field) or []
        if [shape(v) for v in live] != [shape(v) for v in edit["old"]]:
            raise ValueError(f"{field} is not as expected any more: {live}")
        like = live[0] if live else {}
        after[field] = [native(field, v, like) for v in edit["new"]]
        if not after[field]:
            after.pop(field)
    return after


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edits", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--exclusive-write",
        action="store_true",
        help="Confirm that other Omeka writers are paused",
    )
    parser.add_argument("--skip-recent-hours", type=float, default=2)
    parser.add_argument("--item-set-id", type=int)
    args = parser.parse_args()
    try:
        require_exclusive_write(args.apply, args.exclusive_write)
    except ValueError as exc:
        parser.error(str(exc))
    load_dotenv(ROOT / ".env")
    set_id = args.item_set_id or int(os.getenv("ITEM_SET_ID", "10780"))
    edits = json.loads(args.edits.read_text(encoding="utf-8"))["edits"]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for edit in edits:
        grouped.setdefault((edit["kind"], int(edit["id"])), []).append(edit)

    copies = ROOT / "backups" / f"dsp_readiness_{datetime.now():%Y%m%d_%H%M%S_%f}"
    failed = changed = already = 0
    with Omeka(
        os.environ["OMEKA_URL"],
        os.environ["KEY_IDENTITY"],
        os.environ["KEY_CREDENTIAL"],
    ) as api:
        for (kind, rid), group in grouped.items():
            try:
                if kind not in {"items", "media"}:
                    raise ValueError("Expected items or media")
                before = api.get(kind, rid)
                item = (
                    before
                    if kind == "items"
                    else api.get("items", before["o:item"]["o:id"])
                )
                if set_id not in {ref["o:id"] for ref in item["o:item_set"]}:
                    raise ValueError(f"Outside item set {set_id}")
                result = update_record(
                    api,
                    kind,
                    before,
                    plan_record(before, group),
                    apply=args.apply,
                    backup_dir=copies,
                    skip_recent_hours=args.skip_recent_hours,
                    exclusive_write=args.exclusive_write,
                )
                if result.status == "already_applied":
                    already += 1
                    print(f"Already applied {kind}/{rid}")
                elif result.status in {"preview", "updated"}:
                    changed += 1
                    action = "Verified" if args.apply else "Would change"
                    print(f"{action} {kind}/{rid}: {', '.join(result.fields)}")
            except (OSError, ValueError, OmekaError) as exc:
                print(f"{kind}/{rid}: {exc}", file=sys.stderr)
                failed += 1
    print(f"{changed} changes, {already} already applied, {failed} skipped or failed")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
