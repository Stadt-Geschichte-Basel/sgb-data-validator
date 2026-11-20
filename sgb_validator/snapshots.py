"""Read and write metadata snapshots."""

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .api import OmekaAPI, Record

METADATA_FILES = {
    "raw": "download_metadata.json",
    "transformed": "transformation_metadata.json",
    "": "snapshot.json",
}


@dataclass
class Snapshot:
    item_set: Record
    items: list[Record]
    media: list[Record]
    source: str = ""

    @property
    def item_set_id(self) -> int | None:
        return self.item_set.get("o:id")

    def records(self) -> dict[str, list[Record]]:
        return {"items": self.items, "media": self.media}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Replace JSON atomically, with owner-only access."""
    descriptor, filename = tempfile.mkstemp(dir=path.parent)
    tmp = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(
                (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def read_snapshot(directory: Path) -> Snapshot:
    def read(name: str, default: Any = None) -> Any:
        for suffix in ("_transformed", "", "_raw"):
            path = directory / f"{name}{suffix}.json"
            if path.is_file():
                return read_json(path)
        if default is not None:
            return default
        raise ValueError(f"Missing {name} in snapshot {directory}")

    item_set = read("item_set", {})
    items = read("items")
    media = read("media")
    if not isinstance(items, list):
        items = [items]
    if not isinstance(media, list):
        media = [media]
    if not isinstance(item_set, dict) or not all(
        isinstance(record, dict) for record in [*items, *media]
    ):
        raise ValueError(f"Expected Omeka JSON objects in {directory}")
    identifier = item_set.get("@id") or next(
        (
            record["@id"]
            for record in [*items, *media]
            if isinstance(record.get("@id"), str)
        ),
        "",
    )
    source = (
        identifier.rsplit("/api/", 1)[0]
        if isinstance(identifier, str) and "/api/" in identifier
        else ""
    )
    for filename in METADATA_FILES.values():
        path = directory / filename
        if path.exists():
            manifest = read_json(path)
            source = manifest.get("source", source)
            for key, values in (("items_count", items), ("media_count", media)):
                if key in manifest and manifest[key] != len(values):
                    raise ValueError(f"{filename} has a different {key}")
    return Snapshot(item_set, items, media, source)


def write_snapshot(
    directory: Path,
    snapshot: Snapshot,
    status: str,
    *,
    source_directory: Path | None = None,
) -> None:
    directory.mkdir(mode=0o700, parents=True)
    suffix = f"_{status}" if status else ""
    files = {
        name: directory / f"{name}{suffix}.json"
        for name in ("item_set", "items", "media")
    }
    for name, records in {"item_set": snapshot.item_set, **snapshot.records()}.items():
        write_json(files[name], records)
    metadata = {
        "source": snapshot.source,
        "item_set_id": snapshot.item_set_id,
        "items_count": len(snapshot.items),
        "media_count": len(snapshot.media),
        "status": status,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "files": {
            name: str(path.relative_to(directory.parent))
            for name, path in files.items()
        },
    }
    if source_directory is not None:
        metadata["source_directory"] = str(source_directory)
    write_json(directory / METADATA_FILES[status], metadata)


def download_snapshot(api: OmekaAPI, item_set_id: int) -> Snapshot:
    item_set = api.get("item_sets", item_set_id)
    items = api.listing("items", item_set_id=item_set_id)

    def fetch_media(item: Record) -> list[Record]:
        refs = item.get("o:media")
        expected = [ref["o:id"] for ref in refs] if refs is not None else None
        records = api.listing(
            "media",
            item_id=item["o:id"],
            expected_ids=set(expected) if expected is not None else None,
        )
        if expected is not None:
            by_id = {record["o:id"]: record for record in records}
            records = [by_id[rid] for rid in expected]
        if any(record["o:item"]["o:id"] != item["o:id"] for record in records):
            raise ValueError(f"Incorrect media parent for item {item['o:id']}")
        return records

    with ThreadPoolExecutor(max_workers=6) as pool:
        media = [record for group in pool.map(fetch_media, items) for record in group]
    return Snapshot(item_set, items, media, api.base_url)
