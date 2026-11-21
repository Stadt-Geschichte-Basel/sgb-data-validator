"""Read and write metadata snapshots with omeka-s-client."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from omeka_s_client import Snapshot, capture_snapshot, read_snapshot
from omeka_s_client import write_snapshot as _write_snapshot
from omeka_s_client.snapshots import Variant

from .api import Record

__all__ = [
    "Snapshot",
    "capture_snapshot",
    "read_json",
    "read_snapshot",
    "records",
    "write_json",
    "write_snapshot",
]


def records(snapshot: Snapshot) -> dict[str, list[Record]]:
    return {"items": snapshot.items, "media": snapshot.media}


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


def write_snapshot(
    directory: Path,
    snapshot: Snapshot,
    variant: Variant = "",
    *,
    source_directory: Path | None = None,
) -> Path:
    """Write a new snapshot directory and create missing parents."""
    directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    extra = (
        {"source_directory": str(source_directory)}
        if source_directory is not None
        else None
    )
    return _write_snapshot(directory, snapshot, variant=variant, extra=extra)
