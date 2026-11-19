"""Build a reviewed CSV of rights / license edits from the live item set (#44).

Rule (decided on issue #44): the rights text is the rights holder's statement
and wins. The license URI is set to the license the text names. Obvious
typos in the rights text are fixed. Records that need an editor
(RIGHTS_CHECK in generate_triage.py) get no URI change when the text names no
license.

Read-only. Writes one CSV that scripts/fix_safe_validation_errors.py --edits
applies. Nothing is written to Omeka here.

Usage:
    uv run python scripts/build_license_edits.py my_reports/license_edits.csv
"""

import csv
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from generate_triage import RIGHTS_CHECK, suggested_license_uri  # noqa: E402

from validate import OmekaValidator  # noqa: E402

#: Clear spelling errors in rights texts. Meaning does not change.
TYPO_FIXES = [
    (r"Puböic", "Public"),
    (r"gemeinfrai", "gemeinfrei"),
    (r"Historisches Musuem", "Historisches Museum"),
    (r"Historusches Museum", "Historisches Museum"),
    (r"Historische Museum Basel", "Historisches Museum Basel"),
    (r"Museum Base\. Inv\. Inv\.", "Museum Basel, Inv."),
    (r"Inv\. Inv\.", "Inv."),
    (r"(CC BY-SA 4\.0)\.,", r"\1,"),
]


def fix_typos(text: str) -> str:
    for pattern, repl in TYPO_FIXES:
        text = re.sub(pattern, repl, text)
    return text


def first(record: dict, prop: str) -> str:
    values = record.get(prop) or []
    return (values[0].get("@value") or values[0].get("@id") or "") if values else ""


def build_rows(media_records: list[dict]) -> list[dict]:
    """Return CSV rows (kind,id,field,old,new,reason) for the given media."""
    rows = []
    for m in media_records:
        mid = m["o:id"]
        rights, lic = first(m, "dcterms:rights"), first(m, "dcterms:license")
        if not rights or mid in RIGHTS_CHECK:
            continue  # editors decide these records
        fixed = fix_typos(rights)
        if fixed != rights:
            rows.append(
                dict(
                    kind="media",
                    id=mid,
                    field="dcterms:rights",
                    old=rights,
                    new=fixed,
                    reason="typo in rights text",
                )
            )
        uri = suggested_license_uri(fixed)
        if uri and uri != lic:
            reason = "license missing" if not lic else "rights text wins"
            rows.append(
                dict(
                    kind="media",
                    id=mid,
                    field="dcterms:license",
                    old=lic,
                    new=uri,
                    reason=reason,
                )
            )
    return rows


def main() -> int:
    out = Path(sys.argv[1])
    load_dotenv(ROOT / ".env")
    v = OmekaValidator(
        os.environ["OMEKA_URL"].strip().strip('"').rstrip("/"),
        os.environ["KEY_IDENTITY"],
        os.environ["KEY_CREDENTIAL"],
    )
    items = v.fetch_items(int(os.environ.get("ITEM_SET_ID", "10780")))
    expected = int(os.environ.get("EXPECTED_ITEMS", "0"))
    if expected and len(items) != expected:
        raise SystemExit(f"Got {len(items)} items, expected {expected}: truncated?")

    def fetch(item_id: int) -> list[dict]:
        for attempt in range(4):
            try:
                return v.fetch_media(item_id)
            except httpx.TransportError:
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))
        return []

    with ThreadPoolExecutor(6) as pool:
        media = [m for ms in pool.map(fetch, [i["o:id"] for i in items]) for m in ms]
    rows = build_rows(media)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["kind", "id", "field", "old", "new", "reason"]
        )
        w.writeheader()
        w.writerows(rows)
    print(f"{len(items)} items, {len(media)} media, {len(rows)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
