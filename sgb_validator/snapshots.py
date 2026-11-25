"""Read and write metadata snapshots with omeka-s-client."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from omeka_s_client import Snapshot, capture_snapshot, read_snapshot
from omeka_s_client import write_snapshot as _write_snapshot
from omeka_s_client.snapshots import Variant

from .api import Omeka, Record

__all__ = [
    "Snapshot",
    "capture_snapshot",
    "check_saved_totals",
    "fetch_snapshot",
    "read_json",
    "read_snapshot",
    "records",
    "saved_totals",
    "write_json",
    "write_snapshot",
]


def records(snapshot: Snapshot) -> dict[str, list[Record]]:
    return {"items": snapshot.items, "media": snapshot.media}


MANIFESTS = ("download_metadata.json", "transformation_metadata.json", "snapshot.json")
KINDS = ("items", "media")


def fetch_snapshot(api: Omeka, item_set_id: int) -> tuple[Snapshot, dict[str, int]]:
    """Capture a snapshot and compare it with the totals that Omeka reports.

    Return the expected totals. Raise ValueError when a count differs.
    """
    snapshot = capture_snapshot(api, item_set_id)
    page = api.page("items", filters={"item_set_id": item_set_id}, per_page=1)
    if page.total is None:
        raise ValueError("Omeka did not report the number of items")
    totals = {
        "items": page.total,
        # Each item lists its own media. The sum is the media total.
        "media": sum(len(item.get("o:media") or []) for item in snapshot.items),
    }
    mismatch_error(totals, snapshot, "Incomplete fetch")
    return snapshot, totals


def mismatch_error(totals: dict[str, int], snapshot: Snapshot, label: str) -> None:
    actual = records(snapshot)
    differences = [
        f"{kind}: expected {totals[kind]}, found {len(actual[kind])}"
        for kind in KINDS
        if totals[kind] != len(actual[kind])
    ]
    if differences:
        raise ValueError(f"{label}. " + "; ".join(differences))


def saved_totals(directory: Path) -> dict[str, int] | None:
    """Return the expected totals that a snapshot manifest saved, if any."""
    for name in MANIFESTS:
        path = directory / name
        if not path.is_file():
            continue
        saved = read_json(path).get("expected_totals")
        if saved is None:
            continue
        if not isinstance(saved, dict) or not all(
            isinstance(saved.get(kind), int) and saved[kind] >= 0 for kind in KINDS
        ):
            raise ValueError(f"Invalid expected_totals in {name}")
        return {kind: saved[kind] for kind in KINDS}
    return None


def check_saved_totals(directory: Path, snapshot: Snapshot) -> bool:
    """Compare a snapshot with its saved totals. Return False when none exist."""
    totals = saved_totals(directory)
    if totals is None:
        return False
    mismatch_error(totals, snapshot, "Snapshot does not match its saved totals")
    return True


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
    totals: dict[str, int] | None = None,
) -> Path:
    """Write a new snapshot directory and create missing parents."""
    directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    extra: dict[str, Any] = {}
    if source_directory is not None:
        extra["source_directory"] = str(source_directory)
    if totals is not None:
        extra["expected_totals"] = totals
    return _write_snapshot(directory, snapshot, variant=variant, extra=extra or None)
