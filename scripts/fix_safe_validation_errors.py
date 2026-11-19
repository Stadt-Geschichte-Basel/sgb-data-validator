"""Apply reviewed changes to identifier, rights, and license for issue #44."""

import argparse
import csv
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from sgb_validator.api import OmekaAPI, OmekaError
from sgb_validator.writes import update_record

ROOT = Path(__file__).resolve().parent.parent

EDIT_FIELDS: dict[str, dict] = {
    "dcterms:identifier": {
        "type": "literal",
        "property_id": 10,
        "property_label": "Identifier",
        "is_public": True,
    },
    "dcterms:rights": {
        "type": "literal",
        "property_id": 15,
        "property_label": "Rights",
        "is_public": True,
    },
    "dcterms:license": {
        "type": "customvocab:16",
        "property_id": 49,
        "property_label": "License",
        "is_public": True,
        "@language": "en",
    },
}


def plan_edits(rec: dict, rows: list[dict]) -> tuple[dict | None, str | None]:
    """Return (new record, None), or (None, reason) when the record cannot change.

    All rows for one record are applied together, so one record gets one PUT.
    Every row's `old` must match the live value exactly (empty: no value yet).
    """
    new_rec = dict(rec)
    for row in rows:
        field = row.get("field") or "dcterms:identifier"
        if field not in EDIT_FIELDS:
            return None, f"field {field!r} is not allowed"
        values = rec.get(field) or []
        if len(values) > 1 or (values and values[0].get("@value") != row["old"]):
            return None, f"{field} is not {row['old']!r} any more"
        if not values and row["old"]:
            return None, f"{field} is not {row['old']!r} any more"
        base = values[0] if values else dict(EDIT_FIELDS[field])
        new_rec[field] = [{**base, "@value": row["new"]}]
    if all(new_rec.get(k) == rec.get(k) for k in new_rec):
        return None, "no change"
    return new_rec, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edits", "--renames", dest="edits", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-recent-hours", type=float, default=2)
    parser.add_argument("--item-set-id", type=int)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    set_id = args.item_set_id or int(os.getenv("ITEM_SET_ID", "10780"))
    with args.edits.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    counts = Counter(
        (row["kind"], row["new"])
        for row in rows
        if (row.get("field") or "dcterms:identifier") == "dcterms:identifier"
    )
    grouped: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["kind"], int(row["id"])), []).append(row)

    copies = ROOT / "backups" / f"issue44_{datetime.now():%Y%m%d_%H%M%S_%f}"
    failed = changed = 0
    with OmekaAPI(
        os.environ["OMEKA_URL"],
        os.environ["KEY_IDENTITY"],
        os.environ["KEY_CREDENTIAL"],
    ) as api:
        for (kind, rid), group in grouped.items():
            if args.limit and changed >= args.limit:
                break
            try:
                if kind not in {"items", "media"}:
                    raise ValueError("Expected items or media")
                if any(
                    (row.get("field") or "dcterms:identifier") == "dcterms:identifier"
                    and counts[(kind, row["new"])] > 1
                    for row in group
                ):
                    raise ValueError("Identifier appears twice in the CSV")
                before = api.get(kind, rid)
                item = (
                    before
                    if kind == "items"
                    else api.get("items", before["o:item"]["o:id"])
                )
                if set_id not in {ref["o:id"] for ref in item["o:item_set"]}:
                    raise ValueError(f"Outside item set {set_id}")
                proposed, reason = plan_edits(before, group)
                if proposed is None:
                    if reason == "no change":
                        continue
                    raise ValueError(reason)
                update_record(
                    api,
                    kind,
                    before,
                    proposed,
                    apply=args.apply,
                    backup_dir=copies,
                    skip_recent_hours=args.skip_recent_hours,
                )
                changed += 1
                action = "Verified" if args.apply else "Would change"
                print(f"{action} {kind}/{rid}")
            except (OSError, ValueError, OmekaError) as exc:
                print(f"{kind}/{rid}: {exc}", file=sys.stderr)
                failed += 1
    print(f"{changed} changes, {failed} skipped or failed")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
