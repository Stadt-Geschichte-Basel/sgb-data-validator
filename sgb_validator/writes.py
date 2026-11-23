"""Preview and apply guarded writes to Omeka."""

import hashlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

from .api import OmekaClient, OmekaError, Record, Upload, find
from .changes import identifiers, properties, record_changes, ref_id, writable
from .models import Item, Media
from .snapshots import write_json


def check_identifiers(
    api: OmekaClient,
    kind: str,
    payload: Record,
    own_id: int | None = None,
) -> None:
    for value in identifiers(payload):
        if any(record["o:id"] != own_id for record in find(api, kind, value)):
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


@dataclass(frozen=True)
class UpdateResult:
    status: Literal["unchanged", "already_applied", "preview", "updated"]
    fields: tuple[str, ...] = ()
    record: Record | None = None


def model_errors(kind: str, record: Record) -> list[ErrorDetails]:
    models: dict[str, type[BaseModel]] = {"items": Item, "media": Media}
    model = models.get(kind)
    if model is None:
        return []
    # Omeka accepts ID-only references and derives labels on save.
    data = dict(record)
    for key, values in properties(data).items():
        data[key] = [
            {"property_label": key, "is_public": True, **value} for value in values
        ]
    for key in (
        "o:owner",
        "o:resource_class",
        "o:resource_template",
        "o:thumbnail",
        "o:item",
    ):
        value = data.get(key)
        if isinstance(value, dict) and "o:id" in value:
            data[key] = {"@id": "", **value}
    for key in ("o:item_set", "o:media"):
        if isinstance(data.get(key), list):
            data[key] = [
                {"@id": "", **ref} if isinstance(ref, dict) else ref
                for ref in data[key]
            ]
    try:
        model.model_validate(data)
    except ValidationError as exc:
        return exc.errors(include_url=False, include_context=False)
    return []


def check_property_shapes(record: Record) -> None:
    for field, values in record.items():
        if ":" not in field or field.startswith(("o:", "o-cnt:")) or values is None:
            continue
        if not isinstance(values, list) or any(
            not isinstance(value, dict)
            or not isinstance(value.get("property_id"), int)
            or not isinstance(value.get("type"), str)
            or not value["type"]
            for value in values
        ):
            raise ValueError(
                f"{field}: supply a list of native values with type and property_id"
            )


def require_exclusive_write(apply: bool, exclusive_write: bool) -> None:
    if apply and not exclusive_write:
        raise ValueError(
            "Pause other Omeka writers during a maintenance window and "
            "confirm with --exclusive-write"
        )


def update_record(
    api: OmekaClient,
    kind: str,
    before: Record,
    after: Record,
    *,
    apply: bool = False,
    backup_dir: Path | None = None,
    skip_recent_hours: float = 2,
    backup_record: Record | None = None,
    exclusive_write: bool = False,
) -> UpdateResult:
    """Apply updates only while the caller has paused other Omeka writers."""
    require_exclusive_write(apply, exclusive_write)
    if before == after:
        return UpdateResult("unchanged")
    check_property_shapes(after)
    changes = record_changes(kind, before, after)
    if not changes:
        return UpdateResult("unchanged")
    fields = tuple(changes)
    rid = before["o:id"]
    current = api.get(kind, rid)
    expected = {**writable(kind, before), **changes}
    if writable(kind, current) == {
        key: value
        for key, value in expected.items()
        if key not in properties(expected) or value
    }:
        return UpdateResult("already_applied", fields, current)
    if current.get("o:modified") != before.get("o:modified") or writable(
        kind, current
    ) != writable(kind, before):
        raise OmekaError(f"{kind}/{rid} changed since the source read")
    if modified_recently(current, skip_recent_hours):
        raise OmekaError(f"{kind}/{rid} was edited within {skip_recent_hours:g} hours")
    proposed = {**current, **after}
    for key in properties(current).keys() - after.keys():
        proposed.pop(key)
    errors = model_errors(kind, proposed)
    if backup_record is not None:
        # Preserve existing shape defects when replaying trusted backup metadata.
        known = model_errors(kind, backup_record)
        errors = [error for error in errors if error not in known]
    if errors:
        details = ", ".join(
            f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in errors
        )
        raise OmekaError(f"{kind}/{rid} has invalid Omeka metadata: {details}")
    check_identifiers(api, kind, changes, rid)
    if kind == "items" and "o:media" in changes:
        if Counter(ref_id(ref) for ref in current.get("o:media", [])) != Counter(
            ref_id(ref) for ref in changes["o:media"]
        ):
            raise OmekaError(
                f"{kind}/{rid}: media order must contain all current media"
            )
    if not apply:
        return UpdateResult("preview", fields)
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
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = f"{kind}_{rid}_{datetime.now(UTC):%Y%m%d_%H%M%S_%f}.json"
    write_json(backup_dir / name, current)
    latest = api.get(kind, rid)
    if latest.get("o:modified") != current.get("o:modified") or writable(
        kind, latest
    ) != writable(kind, current):
        raise OmekaError(f"{kind}/{rid} changed immediately before the write")
    # The payload holds every RDF value to keep; see the PATCH note above.
    api.patch(kind, rid, payload, replace_rdf_values=True)
    verified = api.get(kind, rid)
    verify_fields(kind, {**writable(kind, current), **changes}, verified)
    return UpdateResult("updated", fields, verified)


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
    check_property_shapes(data)
    for field, values in properties(data).items():
        for value in values:
            literal = value.get("@value")
            if value["type"] == "literal" and (
                not isinstance(literal, str) or not literal.strip(" \t\n\r\0\v")
            ):
                raise ValueError(f"{field}: supply a non-empty string for a literal")
    payload = writable(kind, data)
    if payload.get("o:owner") is None:
        payload.pop("o:owner", None)
    if kind == "items":
        if data.get("o:media"):
            raise ValueError("Create media separately after creating its item")
        if target_id is not None:
            members = {ref["o:id"] for ref in payload.get("o:item_set", [])}
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


def verify_creation(
    kind: str,
    payload: Record,
    actual: Record,
    original: tuple[int, str] | None = None,
) -> None:
    verify_fields(kind, payload, actual)
    if kind != "media":
        return
    for key in ("o:source", "o:ingester"):
        if key in payload and actual.get(key) != payload[key]:
            raise OmekaError(f"media/{actual['o:id']} read-back differs in {key}")
    if ref_id(actual.get("o:item")) != ref_id(payload["o:item"]):
        raise OmekaError(f"media/{actual['o:id']} has a different parent")
    if original and (actual.get("o:size"), actual.get("o:sha256")) != original:
        raise OmekaError(f"media/{actual['o:id']} has a different file size or SHA-256")


def create_record(
    api: OmekaClient,
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
        api.get("items", payload["o:item"]["o:id"])
    check_identifiers(api, kind, payload)
    if not apply:
        return payload
    original = file_digest(file) if file else None
    # A list sends the file as file[0], which matches file_index 0.
    uploads = [Upload(path=file, filename=filename)] if file else None
    record = api.create(kind, payload, files=uploads)
    rid = record["o:id"]
    if on_created is not None:
        on_created(rid)
    verified = api.get(kind, rid)
    verify_creation(kind, payload, verified, original)
    return verified
