"""Back up and recover an item set on the source Omeka instance."""

import hashlib
import json
import os
import re
from collections.abc import Callable, Iterator
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx2

from .api import OmekaAPI, OmekaError, Record
from .changes import identifiers, properties, record_changes, ref_id, writable
from .snapshots import (
    Snapshot,
    download_snapshot,
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
    update_record,
    verify_fields,
)

FILES = ("item_set.json", "items.json", "media.json")
SUPPORTED_INGESTERS = {"upload", "html"}
DEPENDENCIES = {
    "o:item_set": "item_sets",
    "o:site": "sites",
    "o:owner": "users",
    "o:resource_class": "resource_classes",
    "o:resource_template": "resource_templates",
    "o:thumbnail": "assets",
}


def records(snapshot: Snapshot) -> Iterator[tuple[str, Record]]:
    yield "item_sets", snapshot.item_set
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
                    rid = (link.get("@id") or "").rstrip("/").rsplit("/", 1)[-1]
                    rid = int(rid) if rid.isdigit() else None
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


def download_file(
    client: httpx2.Client, url: str, destination: Path | None = None
) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            stream_context = (
                os.fdopen(
                    os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                    "wb",
                )
                if destination is not None
                else nullcontext()
            )
            with stream_context as stream:
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    digest.update(chunk)
                    if stream is not None:
                        stream.write(chunk)
                if stream is not None:
                    stream.flush()
                    os.fsync(stream.fileno())
    except httpx2.HTTPError as exc:
        raise OmekaError(
            f"Original file download failed: {type(exc).__name__}"
        ) from None
    return size, digest.hexdigest()


def check_dependencies(api: OmekaAPI, references: list[Record]) -> list[str]:
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


def backup(api: OmekaAPI, item_set_id: int, directory: Path) -> Record:
    if not api.auth:
        raise OmekaError(
            "Authenticate with access to private records to make a complete backup"
        )
    snapshot = download_snapshot(api, item_set_id)
    write_snapshot(directory, snapshot, "")
    manifest = {
        "version": 1,
        "complete": False,
        "source": api.base_url,
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
    with httpx2.Client(timeout=120, follow_redirects=True) as client:
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
                    ingester == "upload" or media.get("o:sha256") or media.get("o:size")
                ):
                    raise ValueError("Missing original URL")
                if url:
                    if ingester == "html":
                        raise ValueError("HTML media has an unsupported original file")
                    filename = Path(media.get("o:filename") or "").name
                    extension = Path(filename).suffix
                    destination = files / f"{rid}{extension}"
                    size, digest = download_file(client, url, destination)
                    if (size, digest) != (media.get("o:size"), media.get("o:sha256")):
                        raise ValueError(
                            "Original differs from Omeka's file size or SHA-256"
                        )
                    manifest["originals"][str(rid)] = {
                        "path": str(destination.relative_to(directory)),
                        "size": size,
                        "sha256": digest,
                        "filename": Path(media.get("o:source") or filename).name,
                    }
                if ingester == "html" and not isinstance(
                    (media.get("data") or {}).get("html"), str
                ):
                    raise ValueError("Missing HTML ingester data")
            except (OmekaError, OSError, ValueError) as exc:
                manifest["errors"].append(f"media/{rid}: {exc}")
    # Catch changes to membership, ordering, or records during the backup.
    check = download_snapshot(api, item_set_id)
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
    path = (directory / entry["path"]).resolve()
    if not path.is_relative_to((directory / "originals").resolve()):
        raise ValueError("An original file path leaves the backup directory")
    return path


def load_backup(directory: Path) -> tuple[Snapshot, Record, bool]:
    snapshot = read_snapshot(directory)
    manifest_path = directory / "manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    full = manifest.get("version") == 1
    if "version" in manifest and not full:
        raise ValueError("Unknown backup manifest version")
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
        if not manifest.get("complete"):
            raise ValueError(
                "Backup is incomplete: " + "; ".join(manifest.get("errors", []))
            )
        if manifest["source"] != snapshot.source:
            raise ValueError("The backup has a different source URL")
        for name in FILES:
            if file_digest(directory / name)[1] != manifest["metadata"].get(name):
                raise ValueError(f"Backup metadata changed: {name}")
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
            elif ingester == "upload":
                raise ValueError(f"Missing original for media/{rid}")
        if any(parents.values()):
            raise ValueError("Missing media records in the backup")
    return snapshot, manifest, full


def optional_get(api: OmekaAPI, kind: str, rid: int) -> Record | None:
    try:
        return api.get(kind, rid)
    except OmekaError as exc:
        if exc.status != 404:
            raise
        return None


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
    if kind == "media" and data["o:ingester"] == "html":
        data["html"] = data["data"]["html"]
    return remap(kind, data, ids, source)


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
        return (
            ref_id(payload["o:item"]) == ref_id(actual.get("o:item"))
            and original.get("o:sha256") == actual.get("o:sha256")
            and (original.get("data") or {}).get("html")
            == (actual.get("data") or {}).get("html")
        )
    return True


def lock_restore(descriptor: int) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        raise OmekaError("Cannot lock the backup for restore") from exc


def restore(
    api: OmekaAPI,
    directory: Path,
    *,
    apply: bool = False,
    skip_recent_hours: float = 2,
    announce: Callable[[str], None] = print,
) -> None:
    if not api.auth:
        raise OmekaError(
            "Authenticate with access to private records to preview or restore"
        )
    snapshot, manifest, full = load_backup(directory)
    if not snapshot.source or api.base_url != snapshot.source.rstrip("/").removesuffix(
        "/api"
    ):
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
    if apply:
        lock_path = directory / ".restore.lock"
        with os.fdopen(
            os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600), "r+b"
        ) as lock:
            lock_restore(lock.fileno())
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
    else:
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
    api: OmekaAPI,
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
    ledger = (
        read_json(ledger_path)
        if ledger_path.exists()
        else {"source": api.base_url, "backup": fingerprint, "ids": {}, "pending": {}}
    )
    if ledger["source"] != api.base_url or ledger["backup"] != fingerprint:
        raise ValueError("Restore progress belongs to a different backup or instance")
    all_records = list(records(snapshot))
    internal_ids = {record["o:id"] for _, record in all_records}
    ids = {int(old): new for old, new in ledger["ids"].items()}
    current = {}
    for kind, record in all_records:
        old_id = record["o:id"]
        found = optional_get(api, kind, ids.get(old_id, old_id))
        if found is None and old_id in ids:
            raise OmekaError(f"Mapped {kind}/{ids[old_id]} is missing")
        if found is not None:
            current[old_id] = found
            ids[old_id] = found["o:id"]
        elif full:
            announce(f"Recreate {kind}/{old_id}")
        else:
            announce(f"Missing {kind}/{old_id}: metadata backup has no recreation data")
    missing = [
        (kind, record) for kind, record in all_records if record["o:id"] not in current
    ]
    if not full and not apply and missing:
        raise OmekaError(f"{len(missing)} deleted records require a complete backup")
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
        for kind, record in missing:
            for property_id, value in identifiers(record):
                if str(record["o:id"]) not in ledger["pending"] and api.find(
                    kind, value, property_id
                ):
                    raise OmekaError(f"Identifier collision in {kind}: {value!r}")
        return

    created = set()
    initial = ledger.setdefault("initial", {})
    for kind, record in all_records:
        key = str(record["o:id"])
        original = initial.get(key)
        live = current.get(record["o:id"])
        if (
            original is not None
            and live is not None
            and matches_creation(kind, original, live, record)
        ):
            created.add(live["o:id"])

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
            scope = {}
            if kind == "items":
                scope["item_set_id"] = ids[snapshot.item_set_id]
            if kind == "media":
                scope["item_id"] = ref_id(data["o:item"])
            if identifiers(payload):
                property_id, identifier = identifiers(payload)[0]
                candidates = api.find(kind, identifier, property_id)
            else:
                candidates = api.listing(kind, **scope)
            if key in ledger["pending"]:
                earlier = ledger["pending"][key]
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
                "before": [r["o:id"] for r in candidates],
                "payload": payload,
            }
            write_json(ledger_path, ledger)
            current[old_id] = create_record(
                api,
                kind,
                data,
                file=file,
                filename=filename,
                apply=True,
                on_created=lambda new_id, old_id=old_id: persist(old_id, new_id),
            )

    with httpx2.Client(timeout=120, follow_redirects=True) as originals:
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
            originals,
        )


def verify_restored_records(
    api: OmekaAPI,
    directory: Path,
    snapshot: Snapshot,
    manifest: Record,
    full: bool,
    ids: dict[int, int],
    current: dict[int, Record],
    created: set[int],
    skip_recent_hours: float,
    announce: Callable[[str], None],
    originals: httpx2.Client,
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
                ids[ref_id(ref)]
                for ref in record.get("o:media", [])
                if ref_id(ref) in ids
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
            )
            actual = api.get(kind, before["o:id"])
            verify_fields(kind, after, actual)
            if kind == "media" and full:
                verify_original(originals, record, actual, manifest)
            announce(f"Verified {kind}/{actual['o:id']}")
        except (OmekaError, OSError, ValueError) as exc:
            failures += 1
            announce(f"{kind}/{old_id}: {exc}")
    if failures:
        raise OmekaError(f"{failures} records could not be restored or verified")


def verify_original(
    client: httpx2.Client,
    record: Record,
    actual: Record,
    manifest: Record,
) -> None:
    if record.get("o:ingester") == "html":
        if (record.get("data") or {}).get("html") != (actual.get("data") or {}).get(
            "html"
        ):
            raise OmekaError("HTML content differs")
    if actual.get("o:ingester") != record.get("o:ingester"):
        raise OmekaError("Media ingester differs")
    entry = manifest["originals"].get(str(record["o:id"]))
    if not entry:
        return
    expected = entry["size"], entry["sha256"]
    if (actual.get("o:size"), actual.get("o:sha256")) != expected:
        raise OmekaError("Live original file metadata differs")
    url = actual.get("o:original_url")
    if not url:
        raise OmekaError("Missing live original URL")
    if download_file(client, url) != expected:
        raise OmekaError("Live original file bytes differ")
