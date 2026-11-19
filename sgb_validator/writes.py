"""Preview and apply guarded writes to Omeka."""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .api import OmekaAPI, OmekaError, Record
from .changes import identifiers, properties, record_changes, ref_id, writable
from .snapshots import write_json
from .transformations import has_placeholder_media


def check_identifiers(
    api: OmekaAPI,
    kind: str,
    payload: Record,
    own_id: int | None = None,
) -> None:
    for property_id, value in identifiers(payload):
        if any(
            record["o:id"] != own_id for record in api.find(kind, value, property_id)
        ):
            raise OmekaError(f"Identifier collision in {kind}: {value!r}")


def modified_recently(record: Record, hours: float) -> bool:
    value = (record.get("o:modified") or {}).get("@value")
    if not value or hours <= 0:
        return False
    modified = datetime.fromisoformat(value)
    if modified.tzinfo is None:
        modified = modified.replace(tzinfo=UTC)
    return modified > datetime.now(UTC) - timedelta(hours=hours)


def verify_fields(kind: str, expected: Record, actual: Record) -> None:
    projected = writable(kind, actual)
    different = [
        field
        for field, value in writable(kind, expected).items()
        if projected.get(field, [] if isinstance(value, list) else None) != value
    ]
    if different:
        raise OmekaError(
            f"{kind}/{actual['o:id']} read-back differs in {', '.join(different)}"
        )


def file_digest(file: Path) -> tuple[int, str]:
    with file.open("rb") as stream:
        return file.stat().st_size, hashlib.file_digest(stream, "sha256").hexdigest()


def update_record(
    api: OmekaAPI,
    kind: str,
    before: Record,
    after: Record,
    *,
    apply: bool = False,
    backup_dir: Path | None = None,
    skip_recent_hours: float = 2,
) -> Record | None:
    changes = record_changes(kind, before, after)
    if not changes:
        return None
    rid = before["o:id"]
    current = api.get(kind, rid)
    expected = {**writable(kind, before), **changes}
    if writable(kind, current) == {
        key: value
        for key, value in expected.items()
        if key not in properties(expected) or value
    }:
        return current
    if current.get("o:modified") != before.get("o:modified") or writable(
        kind, current
    ) != writable(kind, before):
        raise OmekaError(f"{kind}/{rid} changed since the source read")
    if modified_recently(current, skip_recent_hours):
        raise OmekaError(f"{kind}/{rid} was edited within {skip_recent_hours:g} hours")
    check_identifiers(api, kind, changes, rid)
    if not apply:
        return changes
    if backup_dir is None:
        raise ValueError("Set a private directory for before-edit copies")
    payload = dict(changes)
    if "o:owner" in payload and payload["o:owner"] is None:
        payload["o:owner"] = {"o:id": None}
    if properties(changes):
        # Omeka treats all RDF values as one key in PATCH.
        payload = {**properties(writable(kind, current)), **payload}
        omitted = [
            value["property_id"]
            for field, values in properties(payload).items()
            if not values
            for value in current.get(field, [])
        ]
        if omitted:
            payload["clear_property_values"] = sorted(set(omitted))
    if kind == "items" and "o:media" in changes:
        if sorted(ref_id(ref) for ref in current.get("o:media", [])) != sorted(
            ref_id(ref) for ref in changes["o:media"]
        ):
            raise OmekaError(
                f"{kind}/{rid}: media order must contain all current media"
            )
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = f"{kind}_{rid}_{datetime.now(UTC):%Y%m%d_%H%M%S_%f}.json"
    write_json(backup_dir / name, current)
    latest = api.get(kind, rid)
    if latest.get("o:modified") != current.get("o:modified") or writable(
        kind, latest
    ) != writable(kind, current):
        raise OmekaError(f"{kind}/{rid} changed immediately before the write")
    api.patch(kind, rid, payload)
    verified = api.get(kind, rid)
    verify_fields(kind, {**writable(kind, current), **changes}, verified)
    return verified


def create_payload(
    kind: str,
    data: Record,
    *,
    target_id: int | None = None,
    file: Path | None = None,
    filename: str | None = None,
) -> Record:
    if not isinstance(data, dict):
        raise ValueError("Supply one Omeka JSON object")
    for field, values in properties(data).items():
        for value in values:
            if (
                not isinstance(value, dict)
                or not isinstance(value.get("property_id"), int)
                or not value.get("type")
            ):
                raise ValueError(
                    f"{field}: supply a native property with type and property_id"
                )
    payload = writable(kind, data)
    if payload.get("o:owner") is None:
        payload.pop("o:owner", None)
    if kind == "items":
        if data.get("o:media"):
            raise ValueError("Create media separately after creating its item")
        if target_id is not None:
            members = {ref_id(ref) for ref in payload.get("o:item_set", [])}
            payload["o:item_set"] = [
                {"o:id": rid} for rid in sorted(members | {target_id})
            ]
    if kind == "media":
        parent = target_id if target_id is not None else ref_id(data.get("o:item"))
        if not isinstance(parent, int) or parent <= 0:
            raise ValueError("Select the parent item for the media")
        payload.update(
            {
                key: data[key]
                for key in ("o:ingester", "o:source", "html", "ingest_url")
                if key in data
            }
        )
        payload["o:item"] = {"o:id": parent}
        if file is not None:
            if not file.is_file():
                raise ValueError(f"Missing media file {file}")
            if payload.get("o:ingester", "upload") != "upload":
                raise ValueError("A local file requires the upload ingester")
            payload.update({"o:ingester": "upload", "file_index": 0})
            if has_placeholder_media({"o:filename": filename or file.name}):
                payload["o:is_public"] = False
        elif payload.get("o:ingester") in (None, "upload"):
            raise ValueError("Supply a file with --file or select an Omeka ingester")
        # Keep native media ingester parameters.
        payload.update(
            {
                key: value
                for key, value in data.items()
                if ":" not in key
                and key not in {"data", "thumbnail_display_urls", "file_index"}
            }
        )
    return payload


def create_record(
    api: OmekaAPI,
    kind: str,
    data: Record,
    *,
    target_id: int | None = None,
    file: Path | None = None,
    filename: str | None = None,
    apply: bool = False,
    on_created: Callable[[int], None] | None = None,
) -> Record:
    payload = create_payload(
        kind, data, target_id=target_id, file=file, filename=filename
    )
    if target_id is not None and kind == "items":
        api.get("item_sets", target_id)
    if kind == "media":
        parent = api.get("items", ref_id(payload["o:item"]))
        if file and has_placeholder_media({"o:filename": filename or file.name}):
            if parent.get("o:is_public"):
                raise OmekaError(
                    "Set the parent item to private before attaching a placeholder"
                )
    check_identifiers(api, kind, payload)
    if not apply:
        return payload
    original = file_digest(file) if file else None
    record = api.post(kind, payload, file, filename=filename)
    rid = record["o:id"]
    if on_created is not None:
        on_created(rid)
    verified = api.get(kind, rid)
    verify_fields(kind, payload, verified)
    if kind == "media":
        if ref_id(verified.get("o:item")) != ref_id(payload["o:item"]):
            raise OmekaError(f"media/{rid} has a different parent")
        if original and (verified.get("o:size"), verified.get("o:sha256")) != original:
            raise OmekaError(f"media/{rid} has a different file size or SHA-256")
    return verified
