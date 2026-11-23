"""Back up and recover an item set on the source Omeka instance."""

import hashlib
import json
import os
import re
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit, urlunsplit

from .api import Omeka, OmekaClient, OmekaError, Record, find, optional_get
from .changes import identifiers, properties, record_changes, ref_id, writable
from .snapshots import (
    Snapshot,
    capture_snapshot,
    read_json,
    read_snapshot,
    write_json,
    write_snapshot,
)
from .writes import (
    create_payload,
    create_record,
    file_digest,
    modified_recently,
    require_exclusive_write,
    update_record,
    verify_fields,
)

FILES = ("item_set.json", "items.json", "media.json")
FILE_INGESTERS = {"upload", "url"}
SUPPORTED_INGESTERS = FILE_INGESTERS | {"html"}
DEPENDENCIES = {
    "o:item_set": "item_sets",
    "o:site": "sites",
    "o:owner": "users",
    "o:resource_class": "resource_classes",
    "o:resource_template": "resource_templates",
    "o:thumbnail": "assets",
}


def records(snapshot: Snapshot) -> Iterator[tuple[str, Record]]:
    yield "item_sets", snapshot.item_set or {}
    yield from (("items", item) for item in snapshot.items)
    yield from (("media", medium) for medium in snapshot.media)


def value_objects(record: Record) -> Iterator[Record]:
    for values in properties(record).values():
        for value in values:
            yield value
            if value.get("@annotation"):
                yield from value_objects(value["@annotation"])


def local_resource_url(value: Record, source: str) -> tuple[str, int] | None:
    uri = value.get("@id")
    if not isinstance(uri, str) or not uri.startswith(source + "/api/"):
        return None
    match = re.fullmatch(
        r"/api/(resources|items|media|item_sets)/([0-9]+)",
        urlsplit(uri).path.removeprefix(urlsplit(source).path),
    )
    return (match[1], int(match[2])) if match else None


def relationship_id(value: Record, source: str) -> int | None:
    linked = local_resource_url(value, source)
    return value.get("value_resource_id") or (linked[1] if linked else None)


def external_references(snapshot: Snapshot) -> list[Record]:
    known = {record["o:id"] for _, record in records(snapshot)}
    references = []
    for kind, record in records(snapshot):
        origin = record["o:id"]
        for field, endpoint in DEPENDENCIES.items():
            targets = record.get(field)
            for target in targets if isinstance(targets, list) else [targets]:
                rid = ref_id(target)
                if rid and (endpoint != "item_sets" or rid not in known):
                    references.append(
                        {"from": origin, "to": rid, "kind": endpoint, "field": field}
                    )
        for value in value_objects(record):
            linked = local_resource_url(value, snapshot.source)
            rid = relationship_id(value, snapshot.source)
            if rid and rid not in known:
                references.append(
                    {
                        "from": origin,
                        "to": rid,
                        "kind": linked[0] if linked else "resources",
                        "field": "value_resource_id"
                        if value.get("value_resource_id")
                        else "@id",
                    }
                )
            if value.get("property_id"):
                references.append(
                    {
                        "from": origin,
                        "to": value["property_id"],
                        "kind": "properties",
                        "field": "property_id",
                    }
                )
        for field, links in record.get("@reverse", {}).items():
            for link in links:
                rid = ref_id(link)
                if rid is None:
                    segment = (link.get("@id") or "").rstrip("/").rsplit("/", 1)[-1]
                    rid = int(segment) if segment.isdigit() else None
                if rid and rid not in known:
                    references.append(
                        {
                            "from": rid,
                            "to": origin,
                            "kind": kind,
                            "field": field,
                            "direction": "incoming",
                        }
                    )
    return [
        json.loads(ref)
        for ref in sorted({json.dumps(ref, sort_keys=True) for ref in references})
    ]


def download_file(api: OmekaClient, url: str, destination: Path) -> tuple[int, str]:
    try:
        result = api.download(url, destination)
    except OmekaError as exc:
        raise OmekaError(f"Original file download failed: {exc}") from None
    return result.size, result.sha256


def file_checksum(
    api: OmekaClient, url: str, parent: Path | None = None
) -> tuple[int, str]:
    """Download a file to a private temporary directory and return its digest.

    Pass the backup directory as `parent` to keep large originals off the
    system temporary directory.
    """
    with TemporaryDirectory(dir=parent) as directory:
        return download_file(api, url, Path(directory) / "original")


def check_dependencies(api: OmekaClient, references: list[Record]) -> list[str]:
    errors = []
    checked = {
        (entry["kind"], entry["to"])
        for entry in references
        if entry.get("direction") != "incoming"
    }
    for kind, rid in sorted(checked):
        try:
            api.get(kind, rid)
        except OmekaError as exc:
            errors.append(f"Dependency {kind}/{rid} unavailable: {exc}")
    return errors


def backup(api: Omeka, item_set_id: int, directory: Path) -> Record:
    if not api.has_api_keys:
        raise OmekaError(
            "Authenticate with access to private records to make a complete backup"
        )
    snapshot = capture_snapshot(api, item_set_id)
    write_snapshot(directory, snapshot)
    manifest: Record = {
        "version": 1,
        "complete": False,
        "source": api.installation_url,
        "item_set_id": item_set_id,
        "items_count": len(snapshot.items),
        "media_count": len(snapshot.media),
        "metadata": {name: file_digest(directory / name)[1] for name in FILES},
        "originals": {},
        "errors": [],
        "external_references": external_references(snapshot),
    }
    manifest_file = directory / "manifest.json"
    write_json(manifest_file, manifest)
    files = directory / "originals"
    files.mkdir(mode=0o700)
    manifest["errors"].extend(check_dependencies(api, manifest["external_references"]))
    for media in snapshot.media:
        rid = media["o:id"]
        ingester = media.get("o:ingester")
        url = media.get("o:original_url")
        try:
            if ingester not in SUPPORTED_INGESTERS:
                manifest["errors"].append(
                    f"media/{rid}: unsupported ingester {ingester!r}"
                )
            if not url and (
                ingester in FILE_INGESTERS
                or media.get("o:sha256")
                or media.get("o:size")
            ):
                raise ValueError("Missing original URL")
            if url:
                if ingester == "html":
                    raise ValueError("HTML media has an unsupported original file")
                filename = Path(media.get("o:filename") or "").name
                extension = Path(filename).suffix
                destination = files / f"{rid}{extension}"
                size, digest = download_file(api, url, destination)
                if (size, digest) != (media.get("o:size"), media.get("o:sha256")):
                    raise ValueError(
                        "Original differs from Omeka's file size or SHA-256"
                    )
                source = media.get("o:source") or ""
                original_name = (
                    unquote(urlsplit(source).path).rsplit("/", 1)[-1]
                    if ingester == "url"
                    else Path(source).name
                )
                if (
                    not original_name
                    or Path(original_name).suffix.lower() != extension.lower()
                ):
                    original_name = filename
                manifest["originals"][str(rid)] = {
                    "path": str(destination.relative_to(directory)),
                    "size": size,
                    "sha256": digest,
                    "filename": original_name,
                }
            if ingester == "html" and not isinstance(
                (media.get("data") or {}).get("html"), str
            ):
                raise ValueError("Missing HTML ingester data")
        except (OmekaError, OSError, ValueError) as exc:
            manifest["errors"].append(f"media/{rid}: {exc}")
    # Catch changes to membership, ordering, or records during the backup.
    check = capture_snapshot(api, item_set_id)
    for (kind, before), (other_kind, after) in zip(
        records(snapshot), records(check), strict=False
    ):
        if (
            kind != other_kind
            or before.get("o:id") != after.get("o:id")
            or (
                writable(kind, before) != writable(kind, after)
                or before.get("o:modified") != after.get("o:modified")
                or before.get("o:sha256") != after.get("o:sha256")
            )
        ):
            manifest["errors"].append("Item set changed during backup")
            break
    if (len(check.items), len(check.media)) != (
        len(snapshot.items),
        len(snapshot.media),
    ):
        manifest["errors"].append("Item set counts changed during backup")
    manifest["complete"] = not manifest["errors"]
    write_json(manifest_file, manifest)
    return manifest


def original_path(directory: Path, entry: Record) -> Path:
    path = (directory / Path(entry["path"])).resolve()
    if not path.is_relative_to((directory / "originals").resolve()):
        raise ValueError("An original file path leaves the backup directory")
    return path


def read_manifest(directory: Path) -> Record:
    manifest = directory / "manifest.json"
    return read_json(manifest) if manifest.exists() else {}


def backup_source(directory: Path) -> str:
    manifest = read_manifest(directory)
    return (
        manifest["source"]
        if manifest.get("version") == 1
        else read_snapshot(directory).source
    )


def load_backup(directory: Path) -> tuple[Snapshot, Record, bool]:
    manifest = read_manifest(directory)
    full = manifest.get("version") == 1
    if "version" in manifest and not full:
        raise ValueError("Unknown backup manifest version")
    if full:
        if not manifest.get("complete"):
            raise ValueError(
                "Backup is incomplete: " + "; ".join(manifest.get("errors", []))
            )
        metadata = []
        for name in FILES:
            raw = (directory / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest["metadata"].get(name):
                raise ValueError(f"Backup metadata changed: {name}")
            metadata.append(json.loads(raw))
        item_set, items, media = metadata
        if not isinstance(item_set, dict) or any(
            not isinstance(group, list)
            or any(not isinstance(record, dict) for record in group)
            for group in (items, media)
        ):
            raise ValueError("Expected Omeka JSON objects in verified backup metadata")
        snapshot = Snapshot(manifest["source"], item_set, items, media)
        snapshot_metadata = directory / "snapshot.json"
        if snapshot_metadata.exists() and (
            read_json(snapshot_metadata).get("source") != snapshot.source
        ):
            raise ValueError("The backup has a different source URL")
    else:
        snapshot = read_snapshot(directory)
    if not snapshot.item_set_id:
        raise ValueError("The backup needs the item set metadata")
    for label, count in (
        ("items_count", len(snapshot.items)),
        ("media_count", len(snapshot.media)),
    ):
        if manifest.get(label, count) != count:
            raise ValueError(f"The backup has a different {label}")
    if manifest.get("item_set_id", snapshot.item_set_id) != snapshot.item_set_id:
        raise ValueError("The backup has a different item set ID")
    by_id = {record["o:id"] for _, record in records(snapshot)}
    if len(by_id) != 1 + len(snapshot.items) + len(snapshot.media):
        raise ValueError("Duplicate resource IDs in the backup")
    if full:
        parents = {
            item["o:id"]: [ref_id(ref) for ref in item.get("o:media", [])]
            for item in snapshot.items
        }
        for media in snapshot.media:
            parent = ref_id(media.get("o:item"))
            rid = media["o:id"]
            if parent not in parents or rid not in parents[parent]:
                raise ValueError(f"media/{rid} has no matching parent reference")
            parents[parent].remove(rid)
            ingester = media.get("o:ingester")
            if ingester not in SUPPORTED_INGESTERS:
                raise ValueError(f"media/{rid}: unsupported ingester {ingester!r}")
            entry = manifest["originals"].get(str(rid))
            if entry:
                if file_digest(original_path(directory, entry)) != (
                    entry["size"],
                    entry["sha256"],
                ):
                    raise ValueError(
                        f"Original media/{rid} has a different size or SHA-256"
                    )
            elif ingester in FILE_INGESTERS:
                raise ValueError(f"Missing original for media/{rid}")
        if any(parents.values()):
            raise ValueError("Missing media records in the backup")
    return snapshot, manifest, full


def remap(kind: str, record: Record, ids: dict[int, int], source: str) -> Record:
    result = deepcopy(record)
    for value in value_objects(result):
        target = relationship_id(value, source)
        if target not in ids or ids[target] == target:
            continue
        if value.get("value_resource_id"):
            value["value_resource_id"] = ids[target]
            value.pop("@id", None)
        else:
            uri = urlsplit(value["@id"])
            path = f"{uri.path.rsplit('/', 1)[0]}/{ids[target]}"
            value["@id"] = urlunsplit(uri._replace(path=path))
    key = {"items": "o:item_set", "media": "o:item"}.get(kind)
    if key and result.get(key):
        refs = result[key] if isinstance(result[key], list) else [result[key]]
        for ref in refs:
            rid = ref_id(ref)
            if rid in ids:
                ref["o:id"] = ids[rid]
                ref.pop("@id", None)
    return result


def file_args(
    directory: Path, manifest: Record, record: Record
) -> tuple[Path | None, str | None]:
    entry = manifest.get("originals", {}).get(str(record["o:id"]))
    return (
        (original_path(directory, entry), entry["filename"]) if entry else (None, None)
    )


def recovery_payload(
    kind: str,
    record: Record,
    ids: dict[int, int],
    internal_ids: set[int],
    source: str,
) -> Record:
    data = deepcopy(record)
    # Defer forward links until every destination ID is known.
    unresolved = internal_ids - ids.keys()
    for field, values in properties(data).items():
        data[field] = [
            value
            for value in values
            if not any(
                relationship_id(v, source) in unresolved
                for v in value_objects({field: [value]})
            )
        ]
    if kind == "items":
        data.pop("o:media", None)
    if kind == "media":
        if data["o:ingester"] == "html":
            data["html"] = data["data"]["html"]
        elif data["o:ingester"] == "url":
            # The original remote URL may now serve a different file.
            data["o:ingester"] = "upload"
    return remap(kind, data, ids, source)


def creation_order(
    api: OmekaClient,
    missing: list[tuple[str, Record]],
    source: str,
) -> list[tuple[str, Record]]:
    """Order creates so each required property can retain at least one value."""
    unresolved = {record["o:id"] for _, record in missing}
    requirements: dict[int, list[list[set[int]]]] = {}
    templates: dict[int, set[int]] = {}
    for kind, record in missing:
        rid = record["o:id"]
        template_id = ref_id(record.get("o:resource_template"))
        if template_id is not None and template_id not in templates:
            template = api.get("resource_templates", template_id)
            templates[template_id] = {
                prop
                for entry in template["o:resource_template_property"]
                if entry["o:is_required"]
                and (prop := ref_id(entry["o:property"])) is not None
            }
        required = (
            templates.get(template_id, set()) if template_id is not None else set()
        )
        values: dict[int, list[set[int]]] = {pid: [] for pid in required}
        for field, field_values in properties(record).items():
            for value in field_values:
                pid = value["property_id"]
                if pid in values:
                    values[pid].append(
                        {
                            target
                            for entry in value_objects({field: [value]})
                            if (target := relationship_id(entry, source)) is not None
                            and target in unresolved
                        }
                    )
        for pid, candidates in values.items():
            if not candidates:
                raise OmekaError(
                    f"{kind}/{rid}: missing required property {pid} in backup"
                )
        dependencies = list(values.values())
        if kind == "media":
            parent = ref_id(record.get("o:item"))
            if parent is not None and parent in unresolved:
                dependencies.append([{parent}])
        elif kind == "items":
            dependencies.extend(
                [{set_id}]
                for ref in record.get("o:item_set", [])
                if (set_id := ref_id(ref)) is not None and set_id in unresolved
            )
        requirements[rid] = dependencies

    ordered: list[tuple[str, Record]] = []
    waiting = missing
    while waiting:
        blocked = []
        for kind, record in waiting:
            rid = record["o:id"]
            if any(
                all(targets & unresolved for targets in alternatives)
                for alternatives in requirements[rid]
            ):
                blocked.append((kind, record))
            else:
                ordered.append((kind, record))
                unresolved.remove(rid)
        if len(blocked) == len(waiting):
            labels = ", ".join(f"{kind}/{record['o:id']}" for kind, record in blocked)
            raise OmekaError(f"Required-link cycle blocks recreation of: {labels}")
        waiting = blocked
    return ordered


def matches_creation(
    kind: str, payload: Record, actual: Record, original: Record
) -> bool:
    try:
        verify_fields(kind, payload, actual)
    except OmekaError:
        return False
    provided_terms = {field for field, values in properties(payload).items() if values}
    if provided_terms != properties(actual).keys():
        return False
    if kind == "media":
        if any(
            key in payload and payload[key] != actual.get(key)
            for key in ("o:ingester", "o:source")
        ):
            return False
        return (
            ref_id(payload["o:item"]) == ref_id(actual.get("o:item"))
            and original.get("o:sha256") == actual.get("o:sha256")
            and (original.get("data") or {}).get("html")
            == (actual.get("data") or {}).get("html")
        )
    return True


@contextmanager
def lock_restore(directory: Path) -> Iterator[None]:
    lock_path = directory / ".restore.lock"
    with os.fdopen(os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600), "r+b") as lock:
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise OmekaError("Cannot lock the backup for restore") from exc
        yield


def restore(
    api: Omeka,
    directory: Path,
    *,
    apply: bool = False,
    skip_recent_hours: float = 2,
    announce: Callable[[str], None] = print,
    exclusive_write: bool = False,
) -> None:
    require_exclusive_write(apply, exclusive_write)
    if not api.has_api_keys:
        raise OmekaError(
            "Authenticate with access to private records to preview or restore"
        )
    snapshot, manifest, full = load_backup(directory)
    if not snapshot.source or api.installation_url != snapshot.source.rstrip(
        "/"
    ).removesuffix("/api"):
        raise ValueError("Restore target must match the backup's source instance")
    if not full:
        announce("Metadata recovery for surviving records")
    refs = external_references(snapshot)
    for ref in refs:
        if ref["kind"] in {"resources", "items", "media", "item_sets", "sites"}:
            announce(f"External reference: {ref}")
    errors = check_dependencies(api, refs)
    if errors:
        raise OmekaError("\n".join(errors))

    ledger_path = directory / "restore-progress.json"
    fingerprint = hashlib.sha256(
        json.dumps(list(records(snapshot)), sort_keys=True).encode()
    ).hexdigest()
    with lock_restore(directory) if apply else nullcontext():
        restore_records(
            api,
            directory,
            snapshot,
            manifest,
            full,
            ledger_path,
            fingerprint,
            apply,
            skip_recent_hours,
            announce,
        )


def restore_records(
    api: OmekaClient,
    directory: Path,
    snapshot: Snapshot,
    manifest: Record,
    full: bool,
    ledger_path: Path,
    fingerprint: str,
    apply: bool,
    skip_recent_hours: float,
    announce: Callable[[str], None],
) -> None:
    ledger: Record = (
        read_json(ledger_path)
        if ledger_path.exists()
        else {
            "source": api.installation_url,
            "backup": fingerprint,
            "ids": {},
            "pending": {},
        }
    )
    if ledger["source"] != api.installation_url or ledger["backup"] != fingerprint:
        raise ValueError("Restore progress belongs to a different backup or instance")
    all_records = list(records(snapshot))
    internal_ids = {record["o:id"] for _, record in all_records}
    ids: dict[int, int] = {int(old): new for old, new in ledger["ids"].items()}
    current: dict[int, Record] = {}
    for kind, record in all_records:
        old_id: int = record["o:id"]
        found = optional_get(api, kind, ids.get(old_id, old_id))
        if found is None and old_id in ids:
            raise OmekaError(f"Mapped {kind}/{ids[old_id]} is missing")
        if found is not None:
            current[old_id] = found
            ids[old_id] = found["o:id"]
        elif full:
            suffix = (
                " from the archived original via upload"
                if record.get("o:ingester") == "url"
                else ""
            )
            announce(f"Recreate {kind}/{old_id}{suffix}")
        else:
            announce(f"Missing {kind}/{old_id}: metadata backup has no recreation data")
    missing = [
        (kind, record) for kind, record in all_records if record["o:id"] not in current
    ]
    if full:
        missing = creation_order(api, missing, snapshot.source)
    if not apply:
        for kind, record in all_records:
            if record["o:id"] not in current:
                continue
            live = current[record["o:id"]]
            proposed = remap(kind, record, ids, snapshot.source)
            fields = record_changes(kind, live, proposed)
            if fields:
                recent = modified_recently(live, skip_recent_hours)
                action = "Recent edit; would skip" if recent else "Restore"
                announce(f"{action} {kind}/{live['o:id']}: {', '.join(fields)}")
            else:
                announce(f"Verify surviving {kind}/{live['o:id']}")
        for kind, record in missing if full else []:
            for value in identifiers(record):
                if str(record["o:id"]) not in ledger["pending"] and find(
                    api, kind, value
                ):
                    raise OmekaError(f"Identifier collision in {kind}: {value!r}")
    if not full and missing:
        raise OmekaError(
            f"{len(missing)} deleted records require a complete backup. "
            "No records were written."
        )
    if not apply:
        return

    created: set[int] = set()
    protected = ledger.setdefault("protected", {})
    for old, saved in protected.items():
        current_parent = current.get(int(old))
        if (
            current_parent
            and current_parent.get("o:modified") == saved.get("o:modified")
            and (
                writable("items", {**current_parent, "o:media": saved["o:media"]})
                == writable("items", saved)
            )
        ):
            created.add(current_parent["o:id"])
    initial = ledger.setdefault("initial", {})
    for kind, record in all_records:
        key = str(record["o:id"])
        original = initial.get(key)
        recovered = current.get(record["o:id"])
        if (
            original is not None
            and recovered is not None
            and matches_creation(
                kind,
                original,
                recovered,
                record,
            )
        ):
            created.add(recovered["o:id"])

    def persist(old_id: int, new_id: int) -> None:
        ids[old_id] = new_id
        ledger["ids"][str(old_id)] = new_id
        initial[str(old_id)] = ledger["pending"].pop(str(old_id))["payload"]
        write_json(ledger_path, ledger)
        created.add(new_id)

    if full:
        for kind, record in missing:
            old_id = record["o:id"]
            key = str(old_id)
            data = recovery_payload(kind, record, ids, internal_ids, snapshot.source)
            file, filename = (
                file_args(directory, manifest, record)
                if kind == "media"
                else (None, None)
            )
            payload = create_payload(kind, data, file=file, filename=filename)
            scope: Record = {}
            if kind == "items":
                set_id = snapshot.item_set_id
                assert set_id is not None
                scope["item_set_id"] = ids[set_id]
            if kind == "media":
                scope["item_id"] = ref_id(data["o:item"])
            if identifiers(payload):
                candidates = find(api, kind, identifiers(payload)[0])
            else:
                candidates = api.list(kind, filters=scope, verify=True)
            earlier = ledger["pending"].get(key)
            if earlier is not None:
                candidates = [
                    candidate
                    for candidate in candidates
                    if candidate["o:id"] not in earlier["before"]
                ]
                same = [
                    candidate
                    for candidate in candidates
                    if matches_creation(kind, earlier["payload"], candidate, record)
                ]
                if candidates and len(same) != 1:
                    raise OmekaError(f"Ambiguous pending creation for {kind}/{old_id}")
                if same:
                    persist(old_id, same[0]["o:id"])
                    current[old_id] = same[0]
                    continue
            ledger["pending"][key] = {
                "before": earlier["before"]
                if earlier
                else [r["o:id"] for r in candidates],
                "payload": payload,
            }
            write_json(ledger_path, ledger)

            def record_creation(new_id: int, old: int = old_id) -> None:
                persist(old, new_id)

            current[old_id] = create_record(
                api,
                kind,
                data,
                file=file,
                filename=filename,
                apply=True,
                on_created=record_creation,
            )

    verify_restored_records(
        api,
        directory,
        snapshot,
        manifest,
        full,
        ids,
        current,
        created,
        skip_recent_hours,
        announce,
    )


def verify_restored_records(
    api: OmekaClient,
    directory: Path,
    snapshot: Snapshot,
    manifest: Record,
    full: bool,
    ids: dict[int, int],
    current: dict[int, Record],
    created: set[int],
    skip_recent_hours: float,
    announce: Callable[[str], None],
) -> None:
    failures = 0
    for kind, record in records(snapshot):
        old_id = record["o:id"]
        if old_id not in current:
            failures += 1
            continue
        before = current[old_id]
        after = remap(kind, record, ids, snapshot.source)
        if kind == "items":
            desired = [
                ids[rid]
                for ref in record.get("o:media", [])
                if (rid := ref_id(ref)) is not None and rid in ids
            ]
            live = api.get(kind, before["o:id"])
            before = {
                **before,
                "o:media": live.get("o:media", []),
                "o:modified": live["o:modified"],
            }
            extras = [
                ref_id(ref) for ref in before["o:media"] if ref_id(ref) not in desired
            ]
            after["o:media"] = [{"o:id": rid} for rid in desired + extras]
        try:
            update_record(
                api,
                kind,
                before,
                after,
                apply=True,
                backup_dir=directory / "before-edit",
                skip_recent_hours=0 if before["o:id"] in created else skip_recent_hours,
                backup_record=record,
                exclusive_write=True,
            )
            actual = api.get(kind, before["o:id"])
            verify_fields(kind, after, actual)
            if kind == "media" and full:
                verify_original(
                    api,
                    record,
                    actual,
                    manifest,
                    recreated=ids[old_id] != old_id,
                    parent=directory,
                )
            announce(f"Verified {kind}/{actual['o:id']}")
        except (OmekaError, OSError, ValueError) as exc:
            failures += 1
            announce(f"{kind}/{old_id}: {exc}")
    if failures:
        raise OmekaError(f"{failures} records could not be restored or verified")


def verify_original(
    api: OmekaClient,
    record: Record,
    actual: Record,
    manifest: Record,
    *,
    recreated: bool,
    parent: Path | None = None,
) -> None:
    expected_ingester = record.get("o:ingester")
    if expected_ingester == "url" and recreated:
        expected_ingester = "upload"
    if expected_ingester == "html":
        if (record.get("data") or {}).get("html") != (actual.get("data") or {}).get(
            "html"
        ):
            raise OmekaError("HTML content differs")
    if actual.get("o:ingester") != expected_ingester:
        raise OmekaError("Media ingester differs")
    if actual.get("o:source") != record.get("o:source"):
        raise OmekaError("Media source differs")
    entry = manifest["originals"].get(str(record["o:id"]))
    if not entry:
        return
    expected = entry["size"], entry["sha256"]
    if (actual.get("o:size"), actual.get("o:sha256")) != expected:
        raise OmekaError("Live original file metadata differs")
    url = actual.get("o:original_url")
    if not url:
        raise OmekaError("Missing live original URL")
    if file_checksum(api, url, parent) != expected:
        raise OmekaError("Live original file bytes differ")
