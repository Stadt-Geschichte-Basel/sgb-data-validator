"""Apply the safe, automatic fixes to live Omeka records, one record at a time.

Low risk while co-workers edit in Omeka:
  - Each record is read fresh (GET, cache-busted) before the transform, and
    again right before the PUT. If o:modified changed in between, it is skipped.
  - Residual risk: Omeka has no write precondition. An edit saved in the short
    time between the second read and the PUT is overwritten.
  - Records changed in the last --skip-recent-hours (default 2) are skipped.
  - Only records that the transform actually changes are written (PUT).
  - Each record is saved to backups/fix_<timestamp>/ before its PUT
    (directory 0700, files 0600: records can be non-public).

Fixes are the standard pipeline from src.transformations.transform_item_set_data
(apply_all=True): whitespace / Unicode / HTTPS / DOI isPartOf / private flag, and
for media: empty dcterms:language and dcterms:temporal from the parent item,
empty dcterms:format from o:media_type, "CC-BY…" -> "CC BY…" in dcterms:rights.

Usage:
    uv run python scripts/fix_safe_validation_errors.py            # dry run
    uv run python scripts/fix_safe_validation_errors.py --apply --limit 2
    uv run python scripts/fix_safe_validation_errors.py --apply
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.api import OmekaAPI  # noqa: E402
from src.transformations import transform_item_set_data  # noqa: E402
from validate import OmekaValidator  # noqa: E402


def fresh_get(api: OmekaAPI, kind: str, rid: int) -> dict:
    """GET one record, bypassing the reverse-proxy cache."""
    for attempt in range(4):
        try:
            params = api._add_auth_params({"_": str(time.time_ns())})
            response = api.client.get(
                f"{api.base_url}/api/{kind}/{rid}",
                params=params,
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.TransportError:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def modified_recently(record: dict, hours: float) -> bool:
    value = (record.get("o:modified") or {}).get("@value")
    if not value or hours <= 0:
        return False
    return datetime.fromisoformat(value) > datetime.now(UTC) - timedelta(hours=hours)


def changed_fields(before: dict, after: dict) -> list[str]:
    keys = before.keys() | after.keys()
    return sorted(
        k
        for k in keys
        if json.dumps(before.get(k), sort_keys=True)
        != json.dumps(after.get(k), sort_keys=True)
    )


# Properties that the edit mode may write, with the shape of a new value.
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


def identifier_in_use(api: OmekaAPI, kind: str, value: str, own_id: int) -> bool:
    """True if another record of this kind already has this dcterms:identifier."""
    params = api._add_auth_params(
        {
            "property[0][property]": "10",
            "property[0][type]": "eq",
            "property[0][text]": value,
            "_": str(time.time_ns()),
        }
    )
    response = api.client.get(f"{api.base_url}/api/{kind}", params=params)
    response.raise_for_status()
    return any(r["o:id"] != own_id for r in response.json())


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
    if all(
        json.dumps(new_rec.get(k), sort_keys=True)
        == json.dumps(rec.get(k), sort_keys=True)
        for k in new_rec
    ):
        return None, "no change"
    return new_rec, None


def apply_renames(args, base_url: str, key_id: str, key_cred: str) -> int:
    """Edit identifier, rights or license from a reviewed CSV. Nothing else changes."""
    import csv

    with args.renames.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    new_counts = Counter(
        (r["kind"], r["new"])
        for r in rows
        if (r.get("field") or "dcterms:identifier") == "dcterms:identifier"
    )
    by_record: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        by_record.setdefault((row["kind"], int(row["id"])), []).append(row)
    backup_dir = ROOT / "backups" / f"rename_{datetime.now():%Y%m%d_%H%M%S}"
    stats: Counter[str] = Counter()
    with OmekaAPI(base_url, key_id, key_cred) as api:
        for (kind, rid), group in by_record.items():
            if args.limit and stats["changed"] >= args.limit:
                break
            if any(
                (r.get("field") or "dcterms:identifier") == "dcterms:identifier"
                and new_counts[(kind, r["new"])] > 1
                for r in group
            ):
                print(f"  SKIP [{kind} {rid}] new identifier used twice in CSV")
                stats["skipped"] += 1
                continue
            rec = fresh_get(api, kind, rid)
            new_rec, reason = plan_edits(rec, group)
            if new_rec is None:
                if reason != "no change":
                    print(f"  SKIP [{kind} {rid}] {reason}")
                    stats["skipped"] += 1
                continue
            taken = next(
                (
                    r["new"]
                    for r in group
                    if (r.get("field") or "dcterms:identifier") == "dcterms:identifier"
                    and identifier_in_use(api, kind, r["new"], rid)
                ),
                None,
            )
            if taken:
                print(f"  SKIP [{kind} {rid}] identifier {taken!r} is already in use")
                stats["skipped"] += 1
                continue
            if modified_recently(rec, args.skip_recent_hours):
                print(f"  SKIP [{kind} {rid}] changed < {args.skip_recent_hours} h ago")
                stats["skipped"] += 1
                continue
            if args.apply:
                current = fresh_get(api, kind, rid)
                if current.get("o:modified") != rec.get("o:modified"):
                    print(f"  SKIP [{kind} {rid}] changed during this run")
                    stats["skipped"] += 1
                    continue
                backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                fd = os.open(
                    backup_dir / f"{kind}_{rid}.json",
                    os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                    0o600,
                )
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(rec, f, ensure_ascii=False, indent=2)
            update = api.update_item if kind == "items" else api.update_media
            result = update(rid, new_rec, dry_run=not args.apply)
            if not result.get("validation_passed") or (
                args.apply and not result.get("updated")
            ):
                detail = result.get("errors") or result.get("message")
                print(f"  FAIL [{kind} {rid}] {detail}")
                stats["failed"] += 1
            else:
                stats["changed"] += 1
                shown = "; ".join(
                    f"{(r.get('field') or 'dcterms:identifier').split(':')[1]}: "
                    f"{r['old'][:40]!r} -> {r['new'][:40]!r}"
                    for r in group
                )
                print(f"  {'OK ' if args.apply else 'would'} [{kind} {rid}] {shown}")
    print(
        f"\nchanged: {stats['changed']}  skipped: {stats['skipped']}  "
        f"failed: {stats['failed']}"
    )
    if args.apply and stats["changed"]:
        print(f"Backups: {backup_dir}")
    return 1 if stats["failed"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N changed records")
    ap.add_argument("--skip-recent-hours", type=float, default=2.0)
    ap.add_argument("--item-set-id", type=int, default=None)
    ap.add_argument(
        "--edits",
        "--renames",
        dest="renames",
        type=Path,
        help=(
            "CSV (kind,id,field,old,new,reason): set identifier, rights or license "
            "old -> new only. 'field' may be missing (then dcterms:identifier)."
        ),
    )
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    base_url = os.environ["OMEKA_URL"].strip().strip('"').rstrip("/")
    key_id, key_cred = os.environ["KEY_IDENTITY"], os.environ["KEY_CREDENTIAL"]
    item_set_id = args.item_set_id or int(os.environ.get("ITEM_SET_ID", "10780"))

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}  item set {item_set_id}")
    if args.renames:
        return apply_renames(args, base_url, key_id, key_cred)
    item_ids = [
        i["o:id"]
        for i in OmekaValidator(base_url, key_id, key_cred).fetch_items(item_set_id)
    ]
    print(f"{len(item_ids)} items in item set\n")

    backup_dir = ROOT / "backups" / f"fix_{datetime.now():%Y%m%d_%H%M%S}"
    field_counts: Counter[str] = Counter()
    stats: Counter[str] = Counter()

    with OmekaAPI(base_url, key_id, key_cred) as api:
        for item_id in item_ids:
            if args.limit and stats["changed"] >= args.limit:
                break
            item = fresh_get(api, "items", item_id)
            media = [
                fresh_get(api, "media", m["o:id"]) for m in item.get("o:media", [])
            ]
            _, [new_item], new_media = transform_item_set_data(
                {}, [item], media, apply_all=True, upgrade_https=True
            )

            pairs = [("items", item, new_item)] + [
                ("media", m, nm) for m, nm in zip(media, new_media, strict=False)
            ]
            for kind, before, after in pairs:
                fields = changed_fields(before, after)
                if not fields:
                    continue
                rid = before["o:id"]
                if modified_recently(before, args.skip_recent_hours):
                    stats["skipped_recent"] += 1
                    print(
                        f"  SKIP  [{kind} {rid}] changed < "
                        f"{args.skip_recent_hours} h ago"
                    )
                    continue
                if args.limit and stats["changed"] >= args.limit:
                    break
                update = api.update_item if kind == "items" else api.update_media
                if args.apply:
                    # Omeka PUT replaces the whole record and has no precondition.
                    # Re-read right before the write; skip if someone edited it.
                    current = fresh_get(api, kind, rid)
                    if current.get("o:modified") != before.get("o:modified"):
                        stats["skipped_changed"] += 1
                        print(f"  SKIP  [{kind} {rid}] changed during this run")
                        continue
                    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                    fd = os.open(
                        backup_dir / f"{kind}_{rid}.json",
                        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                        0o600,
                    )
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(before, f, ensure_ascii=False, indent=2)
                result = update(rid, after, dry_run=not args.apply)
                if not result.get("validation_passed"):
                    stats["invalid"] += 1
                    print(f"  INVALID [{kind} {rid}] {result.get('errors')}")
                elif args.apply and not result.get("updated"):
                    stats["failed"] += 1
                    print(f"  FAIL  [{kind} {rid}] {result.get('message')}")
                else:
                    stats["changed"] += 1
                    field_counts.update(f"{kind}: {f}" for f in fields)
                    print(
                        f"  {'OK ' if args.apply else 'would'} [{kind} {rid}] "
                        f"{', '.join(fields)}"
                    )

    verb = "changed" if args.apply else "would change"
    print(
        f"\n{verb}: {stats['changed']}  "
        f"skipped (recent edit): {stats['skipped_recent']}  "
        f"skipped (changed during run): {stats['skipped_changed']}"
        f"  invalid: {stats['invalid']}  failed: {stats['failed']}"
    )
    for field, n in field_counts.most_common():
        print(f"  {n:4d}  {field}")
    if args.apply and stats["changed"]:
        print(f"\nBackups: {backup_dir}")
    return 1 if stats["failed"] or stats["invalid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
