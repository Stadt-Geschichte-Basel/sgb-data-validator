"""Apply reviewed edits that the DSP upload needs.

The edit list is a JSON file. It holds value edits and visibility entries.
A value edit changes all values of one field:

    {"edits": [{"kind": "media", "id": 13654, "field": "dcterms:source",
                "old": [{"type": "uri", "@id": "...", "o:label": "..."}],
                "new": [{"type": "literal", "@value": "Keystone, 119619131 (RM)"}],
                "why": "B5"}]}

"old" must match the live values exactly (type, @value, @id, o:label), in order.
"new" replaces all values of the field. An empty "new" list removes the field.
A new value keeps the visibility of the old values when all old values share
one visibility. When they differ, every new value must set "is_public".
A rerun skips a field that already holds the new values.

A visibility entry changes the visibility of one resource:

    {"kind": "items", "id": 42, "identifier": "SGB_001",
     "visibility": {"expected": false, "target": true}, "why": "R1"}

The live record must hold the identifier. The live o:is_public must equal
"expected". The script sets o:is_public to "target" and touches no value.
A record that already has "target" stays unchanged. One record gets one write,
also when it has value edits and a visibility entry.

The run stops at the first identity mismatch, item-set mismatch, visibility
mismatch, read-back failure, or Omeka error. It lists the records done and not
processed. A value edit that does not match the live values skips the record.
The exit code is 1 after a stop, a skip, or an error.
The script previews by default. --apply --exclusive-write writes, keeps a
before-edit copy, and reads every record back. For a visibility entry, the
read-back checks that every value, including its is_public flag, is unchanged.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sgb_validator.api import Omeka, OmekaClient, OmekaError
from sgb_validator.changes import properties, writable
from sgb_validator.writes import require_exclusive_write, update_record

ROOT = Path(__file__).resolve().parent.parent

#: Omeka property IDs of the Dublin Core terms this script may edit.
PROPERTIES = {
    "dcterms:creator": (2, "Creator"),
    "dcterms:publisher": (5, "Publisher"),
    "dcterms:description": (4, "Description"),
    "dcterms:type": (8, "Type"),
    "dcterms:identifier": (10, "Identifier"),
    "dcterms:source": (11, "Source"),
    "dcterms:language": (12, "Language"),
    "dcterms:relation": (13, "Relation"),
    "dcterms:rights": (15, "Rights"),
    "dcterms:isPartOf": (33, "Is Part Of"),
    "dcterms:temporal": (41, "Temporal Coverage"),
    "dcterms:license": (49, "License"),
}
KEYS = ("type", "@value", "@id", "o:label")


def shape(value: dict[str, Any]) -> dict[str, Any]:
    """The part of a value that an edit compares."""
    return {key: value[key] for key in KEYS if value.get(key) not in (None, "")}


def native(field: str, value: dict[str, Any], like: dict[str, Any]) -> dict[str, Any]:
    """A complete Omeka value. Keep the property of the old value."""
    pid, label = PROPERTIES[field]
    keep = {"@language": like["@language"]} if "@language" in like else {}
    return {
        "property_id": like.get("property_id", pid),
        "property_label": like.get("property_label", label),
        **keep,
        **value,
    }


def visibility(field: str, live: list[dict[str, Any]], new: dict[str, Any]) -> bool:
    """The visibility of a new value. Never guess between mixed old values."""
    if isinstance(new.get("is_public"), bool):
        return new["is_public"]
    seen = {v.get("is_public", True) for v in live}
    if len(seen) > 1:
        raise ValueError(
            f"{field} mixes public and private values. Set is_public on each new value."
        )
    return seen.pop() if seen else True


def plan_record(before: dict[str, Any], edits: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the new record. Raise ValueError when a live value differs."""
    after = dict(before)
    for edit in edits:
        field = edit["field"]
        if field not in PROPERTIES:
            raise ValueError(f"{field} is not allowed")
        live = before.get(field) or []
        if [shape(v) for v in live] == [shape(v) for v in edit["new"]]:
            continue  # already applied
        if [shape(v) for v in live] != [shape(v) for v in edit["old"]]:
            raise ValueError(f"{field} is not as expected any more: {live}")
        like = live[0] if live else {}
        after[field] = [
            {**native(field, v, like), "is_public": visibility(field, live, v)}
            for v in edit["new"]
        ]
        if not after[field]:
            after.pop(field)
    return after


class MismatchError(Exception):
    """A mismatch that stops the whole run."""


def plan_visibility(before: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """Return the record with the target visibility. Touch no value."""
    live_ids = [v.get("@value") for v in before.get("dcterms:identifier") or []]
    if entry["identifier"] not in live_ids:
        raise MismatchError(f"Identifier {entry['identifier']!r} is not in {live_ids}")
    want = entry["visibility"]
    live = before.get("o:is_public")
    if live == want["target"]:
        return before
    if live != want["expected"]:
        raise MismatchError(f"o:is_public is {live}, expected {want['expected']}")
    return {**before, "o:is_public": want["target"]}


def check_read_back(
    kind: str, before: dict[str, Any], after: dict[str, Any], verified: dict[str, Any]
) -> None:
    """Every value, with its is_public flag, equals the plan."""
    planned = properties(writable(kind, after))
    actual = properties(writable(kind, verified))
    for name in planned.keys() | actual.keys() | properties(before).keys():
        if actual.get(name, []) != planned.get(name, []):
            raise MismatchError(
                f"{kind}/{verified['o:id']} read-back differs in {name}"
            )
    if verified.get("o:is_public") != after["o:is_public"]:
        raise MismatchError(
            f"{kind}/{verified['o:id']} read-back differs in o:is_public"
        )


def run(
    api: OmekaClient,
    edits: list[dict[str, Any]],
    *,
    apply: bool = False,
    exclusive_write: bool = False,
    set_id: int = 10780,
    backup_dir: Path | None = None,
    skip_recent_hours: float = 2,
) -> dict[str, Any]:
    """Process each record once. A mismatch or read-back failure stops the run."""
    require_exclusive_write(apply, exclusive_write)
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for edit in edits:
        grouped.setdefault((edit["kind"], int(edit["id"])), []).append(edit)
    names = [f"{kind}/{rid}" for kind, rid in grouped]
    n = {"changed": 0, "unchanged": 0, "skipped": 0, "failed": 0}
    stopped = False
    for index, ((kind, rid), group) in enumerate(grouped.items()):
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
                raise MismatchError(f"Outside item set {set_id}")
            entries = [e for e in group if "visibility" in e]
            after = plan_record(before, [e for e in group if "field" in e])
            if entries:
                after = plan_visibility(after, entries[0])
            result = update_record(
                api,
                kind,
                before,
                after,
                apply=apply,
                backup_dir=backup_dir,
                skip_recent_hours=skip_recent_hours,
                exclusive_write=exclusive_write,
            )
            if result.status == "updated" and entries and result.record:
                check_read_back(kind, before, after, result.record)
            if result.status in {"unchanged", "already_applied"}:
                n["unchanged"] += 1
                print(f"Unchanged {names[index]} ({result.status})")
            else:
                n["changed"] += 1
                action = "Verified" if apply else "Would change"
                print(f"{action} {names[index]}: {', '.join(result.fields)}")
        except (MismatchError, OmekaError) as exc:
            print(f"{names[index]}: {exc}", file=sys.stderr)
            n["failed"] += 1
            stopped = True
            print(f"Done: {names[:index]}", file=sys.stderr)
            print(f"Not processed: {names[index + 1 :]}", file=sys.stderr)
            break
        except ValueError as exc:
            print(f"{names[index]}: {exc}", file=sys.stderr)
            n["skipped"] += 1
        except OSError as exc:
            print(f"{names[index]}: {exc}", file=sys.stderr)
            n["failed"] += 1
    print(", ".join(f"{v} {k}" for k, v in n.items()))
    return {
        **n,
        "stopped": stopped,
        "not_processed": names[index + 1 :] if stopped else [],
    }


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
    copies = ROOT / "backups" / f"dsp_readiness_{datetime.now():%Y%m%d_%H%M%S_%f}"
    with Omeka(
        os.environ["OMEKA_URL"],
        os.environ["KEY_IDENTITY"],
        os.environ["KEY_CREDENTIAL"],
    ) as api:
        counts = run(
            api,
            edits,
            apply=args.apply,
            exclusive_write=args.exclusive_write,
            set_id=set_id,
            backup_dir=copies,
            skip_recent_hours=args.skip_recent_hours,
        )
    return int(bool(counts["stopped"] or counts["failed"] or counts["skipped"]))


if __name__ == "__main__":
    raise SystemExit(main())
