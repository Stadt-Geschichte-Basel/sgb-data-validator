"""Build the German work list for co-workers and post it to issue #44.

Runs the validator on the live item set, groups the errors by the Omeka user
who created each record, adds a suggested fix where one can be derived, and
prints one Markdown block. With --post it updates the work-list comment on the
issue in place (it creates the comment on the first run).

Extra checks (only for this list):
  - media identifier number != parent item number -> suggest the right one
  - item identifier does not start with "abb<digit>" ("dataset<digit>" is also
    allowed: contributed datasets such as KNIL item 11181)
  - license named in dcterms:rights != dcterms:license URI

Usage:
    uv run python scripts/generate_triage.py            # print Markdown
    uv run python scripts/generate_triage.py --post     # update issue comment
"""

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from validate import OmekaValidator  # noqa: E402

REPO = "Stadt-Geschichte-Basel/sgb-data-validator"
ISSUE = 44
MARKER = "<!-- arbeitsliste:generate_triage.py -->"
RECENT_DAYS = 14

#: Omeka user id -> GitHub login, for @mentions. Fill in to notify people.
GITHUB_LOGINS: dict[int, str] = {}

#: Records that need a team decision. They go to one section, not to co-workers.
JULY_2025_BLOCK = {
    f"{p}{n}"
    for p in ("abb", "m")
    for n in (92486, 92806, 93036, 93170, 93240, 93262, 93490)
}
DECISIONS = {
    "data_story": "Data Stories ohne Identifier: Identifier-Schema festlegen. "
    "Danach kann ein Skript alle Identifier setzen.",
    "july_2025": "Juli-2025-Block (Marktplatz/Mustermesse, Items 12622–12661) "
    "nutzt die Identifier der Serie vom Mai 2025 (Items 12373–12390). "
    "Festlegen, welche Seite neue Identifier bekommt.",
    "abb21892": "abb21892 (Items 12755 / 13553): öffentliche URL auf "
    "forschung.stadtgeschichtebasel.ch. Festlegen, welches Objekt die neue ID bekommt.",
    "stub_13371": "Media 13371 «Topfhelm» ist ein Platzhalter ohne Metadaten. "
    "Ergänzen oder löschen.",
}

FIELD_LABELS = {
    "dcterms:identifier": "Identifier",
    "dcterms:title": "Title",
    "o:title": "Title",
    "dcterms:description": "Description",
    "dcterms:rights": "Rights",
    "dcterms:license": "License",
    "dcterms:temporal": "Temporal Coverage",
    "dcterms:language": "Language",
    "dcterms:format": "Format",
}
GROUP_ORDER = [
    "Doppelte Identifier",
    "Fehlende Pflichtfelder",
    "Falscher Inhalt",
    "Rights und License passen nicht",
    "Sonstiges",
]

# License families: name in dcterms:rights text vs. dcterms:license URI.
RIGHTS_PATTERNS = [
    ("CC BY-NC-SA", r"cc[\s-]*by[\s-]*nc[\s-]*sa"),
    ("CC BY-NC-ND", r"cc[\s-]*by[\s-]*nc[\s-]*nd"),
    ("CC BY-NC", r"cc[\s-]*by[\s-]*nc\b"),
    ("CC BY-ND", r"cc[\s-]*by[\s-]*nd\b|attribution-noderivatives"),
    ("CC BY-SA", r"cc[\s-]*by[\s-]*sa|attribution-sharealike"),
    ("CC BY", r"cc[\s-]*by\b|creative commons attribution 4"),
    ("Public Domain", r"cc0|public\s*domain|gemeinfrei"),
    ("In Copyright", r"in copyright|urheberrechtlich"),
]
LICENSE_URI_FAMILY = [
    ("/by-nc-sa/", "CC BY-NC-SA"),
    ("/by-nc-nd/", "CC BY-NC-ND"),
    ("/by-nc/", "CC BY-NC"),
    ("/by-nd/", "CC BY-ND"),
    ("/by-sa/", "CC BY-SA"),
    ("/by/", "CC BY"),
    ("/publicdomain/", "Public Domain"),
    ("rightsstatements.org/vocab/InC", "In Copyright"),
]


@dataclass
class Entry:
    kind: str  # "Item" | "Media"
    rid: int
    record: dict
    problems: list[str] = field(default_factory=list)
    groups: set[str] = field(default_factory=set)
    decision: str | None = None


def first_value(record: dict, prop: str) -> str | None:
    values = record.get(prop) or []
    return (values[0].get("@value") or values[0].get("@id")) if values else None


def title_of(record: dict) -> str:
    t = first_value(record, "dcterms:title") or record.get("o:title") or "(ohne Titel)"
    t = " ".join(t.split())
    return t if len(t) <= 60 else t[:57] + "…"


def rights_family(text: str) -> str | None:
    low = text.lower()
    for name, pattern in RIGHTS_PATTERNS:
        if re.search(pattern, low):
            return name
    return None


def license_family(uri: str) -> str | None:
    return next((name for part, name in LICENSE_URI_FAMILY if part in uri), None)


def parent_number(item: dict | None) -> str | None:
    m = re.match(r"abb(\d+)", first_value(item or {}, "dcterms:identifier") or "")
    return m.group(1) if m else None


def suggest_media_identifier(media: dict, parent: dict | None) -> str | None:
    """Return the expected identifier if the media identifier does not fit its item."""
    ident = first_value(media, "dcterms:identifier")
    number = parent_number(parent)
    if not ident or not number:
        return None
    m = re.match(r"(m|abb)(\d+)(.*)", ident)
    if m and m.group(1) == "m" and m.group(2) == number:
        return None
    suffix = m.group(3) if m else ""
    return f"m{number}{suffix}"


def classify_error(entry: Entry, field_name: str, msg: str, title_by_id) -> None:
    dup = re.search(r"Duplicate identifier '([^']+)' found in \w+: \[([\d, ]+)\]", msg)
    if dup:
        others = [int(x) for x in dup.group(2).split(",") if int(x) != entry.rid]
        other_titles = {title_by_id(entry.kind, o) for o in others}
        refs = ", ".join(f"{entry.kind} {o}" for o in others)
        some = "einem der beiden" if len(others) == 1 else "allen ausser einem"
        if other_titles == {title_of(entry.record)}:
            text = (
                f"Gleicher Titel und Identifier wie {refs}. Prüfen: Ist es "
                "dasselbe Objekt, die Doppel löschen (einer bleibt). Sonst "
                f"{some} einen neuen Identifier geben."
            )
        else:
            text = (
                f"Gleicher Identifier `{dup.group(1)}` wie {refs} "
                f"(«{'», «'.join(sorted(other_titles))}»). "
                f"{some[0].upper() + some[1:]} einen neuen Identifier geben."
            )
        entry.problems.append(text)
        entry.groups.add("Doppelte Identifier")
        return
    base = field_name.split("[")[0].split(".")[0]
    label = FIELD_LABELS.get(base, base)
    if "required" in msg.lower() or "valid string" in msg:
        text = f"Pflichtfeld **{label}** fehlt."
        if text not in entry.problems:
            entry.problems.append(text)
        entry.groups.add("Fehlende Pflichtfelder")
    elif base == "dcterms:language":
        value = msg.rsplit(":", 1)[-1].strip()
        entry.problems.append(
            f"**Language** enthält «{value}». Sprachcode eintragen (z. B. `de`)."
        )
        entry.groups.add("Falscher Inhalt")
    elif "vocabulary" in msg.lower() or "Invalid" in msg:
        entry.problems.append(f"**{label}**: Wert nicht im Vokabular ({msg}).")
        entry.groups.add("Falscher Inhalt")
    else:
        entry.problems.append(f"**{label}**: {msg}")
        entry.groups.add("Sonstiges")


def build_entries(validator: OmekaValidator) -> list[Entry]:
    items = {i["o:id"]: i for i in validator.items_data}
    media = {m["o:id"]: m for m in validator.media_data}
    records = {"Item": items, "Media": media}

    def title_by_id(kind: str, rid: int) -> str:
        return title_of(records[kind].get(rid, {}))

    entries: dict[tuple[str, int], Entry] = {}

    def entry(kind: str, rid: int) -> Entry:
        key = (kind, rid)
        if key not in entries:
            entries[key] = Entry(kind, rid, records[kind].get(rid, {}))
        return entries[key]

    # Extra check: media identifier must fit the parent item identifier.
    suggestions: dict[int, str] = {}
    for mid, m in media.items():
        parent = items.get((m.get("o:item") or {}).get("o:id"))
        expected = suggest_media_identifier(m, parent)
        if expected:
            suggestions[mid] = expected

    for err in validator.errors:
        classify_error(
            entry(err.resource_type, err.resource_id), err.field, err.error, title_by_id
        )

    # Media numbers per parent item, to propose at most one new item identifier.
    numbers_by_parent: dict[int, set[str]] = defaultdict(set)
    for m in media.values():
        own = re.match(r"m(\d+)", first_value(m, "dcterms:identifier") or "")
        parent_id = (m.get("o:item") or {}).get("o:id")
        if own and parent_id is not None:
            numbers_by_parent[parent_id].add(own.group(1))
    proposed = Counter(suggestions.values())

    clear_fixes: set[int] = set()
    for mid, expected in suggestions.items():
        e = entry("Media", mid)
        current = first_value(e.record, "dcterms:identifier") or ""
        parent = items.get((e.record.get("o:item") or {}).get("o:id"), {})
        parent_ident = first_value(parent, "dcterms:identifier")
        numbers = numbers_by_parent.get(parent.get("o:id"), set())
        candidate = f"abb{next(iter(numbers))}" if len(numbers) == 1 else None
        own = re.match(r"m(\d+)", current)
        if len(validator.item_identifiers.get(parent_ident, [])) > 1 and own:
            # The item identifier is itself a duplicate: the item may be wrong.
            text = (
                f"Identifier `{current}` passt nicht zum Objekt `{parent_ident}` "
                f"(Item {parent['o:id']}), und `{parent_ident}` ist doppelt "
                "vergeben."
            )
            if candidate and candidate not in validator.item_identifiers:
                text += (
                    f" **Vorschlag: Item {parent['o:id']} auf `{candidate}` ändern.**"
                )
            else:
                text += " Prüfen, ob das Item oder die Media falsch ist."
        elif expected in validator.media_identifiers:
            used_by = ", ".join(
                f"Media {i}" for i in validator.media_identifiers[expected]
            )
            text = (
                f"Identifier `{current}` passt nicht zum Objekt `{parent_ident}`. "
                f"`{expected}` ist aber schon vergeben ({used_by}). Prüfen."
            )
        elif proposed[expected] > 1:
            text = (
                f"Identifier `{current}` passt nicht zum Objekt `{parent_ident}`. "
                f"`{expected}` wird für mehrere Media vorgeschlagen. Prüfen."
            )
        elif not current.startswith("m"):
            text = (
                f"Media-Identifier muss mit `m` beginnen. **Vorschlag: `{expected}`**."
            )
            clear_fixes.add(mid)
        else:
            text = (
                f"Identifier `{current}` passt nicht zum Objekt `{parent_ident}`. "
                f"**Vorschlag: `{expected}`**."
            )
            clear_fixes.add(mid)
        e.problems.insert(0, text)
        e.groups.add(
            "Doppelte Identifier"
            if "Doppelte Identifier" in e.groups
            else "Falscher Inhalt"
        )

    # Duplicate pairs: if one side has a clear fix, the other side is fine.
    for mid in clear_fixes:
        current = first_value(media[mid], "dcterms:identifier")
        for other_id in validator.media_identifiers.get(current, []):
            if other_id != mid and other_id not in suggestions:
                other = entries.get(("Media", other_id))
                if other and other.groups == {"Doppelte Identifier"}:
                    del entries[("Media", other_id)]

    # Extra check: item identifier spelling.
    for iid, item in items.items():
        ident = first_value(item, "dcterms:identifier")
        if ident and not re.match(r"abb\d|dataset\d", ident):
            e = entry("Item", iid)
            e.problems.append(
                f"Identifier `{ident}` beginnt nicht mit `abb` + Ziffer "
                "(oder `dataset` + Ziffer). "
                "Schreibweise prüfen."
            )
            e.groups.add("Falscher Inhalt")

    # Extra check: rights text vs. license URI.
    for mid, m in media.items():
        rights, lic = (
            first_value(m, "dcterms:rights"),
            first_value(m, "dcterms:license"),
        )
        if not rights or not lic:
            continue
        r_fam, l_fam = rights_family(rights), license_family(lic)
        if r_fam and l_fam and r_fam != l_fam:
            e = entry("Media", mid)
            e.problems.append(
                f"Rights nennt «{r_fam}», License ist «{l_fam}» (`{lic}`). Angleichen."
            )
            e.groups.add("Rights und License passen nicht")

    for e in entries.values():
        ident = first_value(e.record, "dcterms:identifier") or ""
        if not ident and title_of(e.record).startswith("Data Story"):
            e.decision = "data_story"
        elif ident in JULY_2025_BLOCK:
            e.decision = "july_2025"
        elif ident == "abb21892":
            e.decision = "abb21892"
        elif (e.kind, e.rid) == ("Media", 13371):
            e.decision = "stub_13371"
    return list(entries.values())


def owner_names(validator: OmekaValidator, owner_ids: set[int]) -> dict[int, str]:
    names = {}
    for uid in owner_ids:
        try:
            r = validator.client.get(
                f"{validator.base_url}/api/users/{uid}",
                params=validator._add_auth_params({}),
            )
            r.raise_for_status()
            names[uid] = r.json().get("o:name") or f"Benutzer {uid}"
        except Exception:  # noqa: BLE001
            names[uid] = f"Benutzer {uid}"
    return names


def render(entries: list[Entry], validator: OmekaValidator, admin: str) -> str:
    def owner(e: Entry) -> int | None:
        return (e.record.get("o:owner") or {}).get("o:id")

    def created(e: Entry) -> datetime | None:
        v = (e.record.get("o:created") or {}).get("@value")
        return datetime.fromisoformat(v) if v else None

    cutoff = datetime.now(UTC) - timedelta(days=RECENT_DAYS)
    todo = [e for e in entries if not e.decision]
    decided = [e for e in entries if e.decision]
    names = owner_names(validator, {owner(e) for e in todo if owner(e)})

    def line(e: Entry) -> str:
        seg = "item" if e.kind == "Item" else "media"
        ident = first_value(e.record, "dcterms:identifier")
        c = created(e)
        new = " 🆕" if c and c >= cutoff else ""
        ident_txt = f" `{ident}`" if ident else ""
        return (
            f"- [ ] [{e.kind} {e.rid}]({admin}/{seg}/{e.rid}/edit) "
            f"«{title_of(e.record)}»{ident_txt}{new}"
            f" — {' '.join(e.problems)}"
        )

    out = [
        MARKER,
        f"## Arbeitsliste Omeka (Stand {date.today():%d.%m.%Y})",
        "",
        f"**{len(todo)} Datensätze** zu korrigieren · "
        f"{sum(1 for e in todo if (c := created(e)) and c >= cutoff)} davon neu "
        f"(🆕 = in den letzten {RECENT_DAYS} Tagen erstellt, bitte zuerst) · "
        f"Fehler total: {len(validator.errors)}",
        "",
        "So geht's: Link öffnen → Feld korrigieren → speichern. "
        "Erledigte Punkte verschwinden beim nächsten Lauf (Häkchen sind optional).",
        "Vor dem Ändern eines Identifiers: öffentliche URL auf "
        "forschung.stadtgeschichtebasel.ch prüfen. Wenn das Objekt dort schon "
        "verlinkt ist, lieber das andere Objekt umbenennen.",
        "",
        "_Automatisch erzeugt mit `scripts/generate_triage.py`. Leere Felder "
        "(Language, Temporal Coverage, Format) und die Schreibweise «CC BY» "
        "korrigiert ein Skript; dafür ist nichts zu tun._",
    ]

    by_owner: dict[int | None, list[Entry]] = defaultdict(list)
    for e in todo:
        by_owner[owner(e)].append(e)
    for uid, group in sorted(by_owner.items(), key=lambda kv: -len(kv[1])):
        name = names.get(uid, "Unbekannt") if uid else "Unbekannt"
        login = f" @{GITHUB_LOGINS[uid]}" if uid in GITHUB_LOGINS else ""
        out += ["", f"### {name}{login} — {len(group)}"]
        for g in GROUP_ORDER:
            rows = [
                e
                for e in group
                if g in e.groups and min(e.groups, key=GROUP_ORDER.index) == g
            ]
            if not rows:
                continue
            rows.sort(
                key=lambda e: (not (created(e) and created(e) >= cutoff), e.kind, e.rid)
            )
            out += ["", f"**{g}**", ""] + [line(e) for e in rows]

    if decided:
        out += ["", "### Entscheidung nötig", ""]
        for key, text in DECISIONS.items():
            rows = [e for e in decided if e.decision == key]
            if rows:
                ids = ", ".join(
                    f"{e.kind} {e.rid}"
                    for e in sorted(rows, key=lambda e: (e.kind, e.rid))
                )
                noun = "Datensatz" if len(rows) == 1 else "Datensätze"
                out.append(f"- [ ] {text} ({len(rows)} {noun}: {ids})")
    return "\n".join(out) + "\n"


def post(body: str) -> None:
    login = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    jq = (
        f'.[] | select(.user.login == "{login}") '
        f'| select(.body | startswith("{MARKER}")) | .id'
    )
    found = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/{REPO}/issues/{ISSUE}/comments",
            "--jq",
            jq,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    existing = found[0] if found else None
    if existing:
        endpoint, method = f"repos/{REPO}/issues/comments/{existing}", "PATCH"
    else:
        endpoint, method = f"repos/{REPO}/issues/{ISSUE}/comments", "POST"
    result = subprocess.run(
        ["gh", "api", "-X", method, endpoint, "--input", "-"],
        input=json.dumps({"body": body}),
        check=True,
        capture_output=True,
        text=True,
    )
    print(
        f"{'Updated' if existing else 'Created'}: "
        f"{json.loads(result.stdout)['html_url']}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--post", action="store_true", help=f"update the comment on issue #{ISSUE}"
    )
    ap.add_argument("--item-set-id", type=int, default=None)
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    base_url = os.environ["OMEKA_URL"].strip().strip('"').rstrip("/")
    item_set_id = args.item_set_id or int(os.environ.get("ITEM_SET_ID", "10780"))
    # enable_profiling keeps the raw records (items_data / media_data) in memory.
    validator = OmekaValidator(
        base_url,
        os.environ["KEY_IDENTITY"],
        os.environ["KEY_CREDENTIAL"],
        enable_profiling=True,
    )
    with contextlib.redirect_stdout(sys.stderr):  # progress output
        validator.validate_item_set(item_set_id)
    print(
        f"Validated {validator.validated_items} items, "
        f"{validator.validated_media} media, "
        f"{len(validator.errors)} errors",
        file=sys.stderr,
    )

    expected_ids = {
        m["o:id"] for i in validator.items_data for m in i.get("o:media") or []
    }
    missing = expected_ids - {m["o:id"] for m in validator.media_data}
    if missing:
        print(
            f"Error: {len(missing)} media not fetched (e.g. {sorted(missing)[:5]}). "
            "The list is incomplete; not posting.",
            file=sys.stderr,
        )
        if args.post:
            return 1

    site = base_url[: -len("/api")] if base_url.endswith("/api") else base_url
    body = render(build_entries(validator), validator, f"{site}/admin")
    if len(body) > 65536:
        print(
            f"Error: {len(body)} characters, GitHub limit is 65536. Not posting.",
            file=sys.stderr,
        )
        if args.post:
            return 1
    if args.post:
        post(body)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
