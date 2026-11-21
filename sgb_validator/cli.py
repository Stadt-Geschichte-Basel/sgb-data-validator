"""The sgb command-line interface."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from .api import Omeka, OmekaError, Record
from .links import check_links
from .reports import export_validation_csv, print_report, save_report
from .snapshots import (
    Snapshot,
    capture_snapshot,
    read_snapshot,
    records,
    write_snapshot,
)
from .transformations import transform_item_set_data
from .validation import validate_records
from .vocabularies import VocabularyLoader

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
BaseURL = Annotated[str | None, typer.Option("--base-url", envvar="OMEKA_URL")]
ItemSetID = Annotated[int | None, typer.Option(envvar="ITEM_SET_ID")]
Identity = Annotated[str | None, typer.Option(envvar="KEY_IDENTITY")]
Credential = Annotated[str | None, typer.Option(envvar="KEY_CREDENTIAL")]
ExclusiveWrite = Annotated[
    bool, typer.Option(help="Confirm that other Omeka writers are paused.")
]


class Severity(StrEnum):
    warning = "warning"
    error = "error"


@contextmanager
def command_errors() -> Iterator[None]:
    try:
        yield
    except (OmekaError, OSError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None


def connect(
    base_url: str | None, identity: str | None, credential: str | None
) -> Omeka:
    if not base_url:
        raise ValueError("Set OMEKA_URL or pass --base-url")
    return Omeka(base_url, identity, credential)


def target(item_set_id: int | None) -> int:
    if item_set_id is None:
        raise ValueError("Set ITEM_SET_ID or pass --item-set-id")
    return item_set_id


def dated_dir(root: Path, prefix: str, item_set_id: int | None) -> Path:
    label = item_set_id if item_set_id is not None else "offline"
    return root / f"{prefix}_itemset_{label}_{datetime.now():%Y%m%d_%H%M%S_%f}"


@app.command()
def download(
    item_set_id: ItemSetID = None,
    base_url: BaseURL = None,
    key_identity: Identity = None,
    key_credential: Credential = None,
    output_dir: Path = Path("data"),
) -> None:
    """Download the metadata for an Omeka item set."""
    with command_errors(), connect(base_url, key_identity, key_credential) as api:
        snapshot = capture_snapshot(api, target(item_set_id))
        directory = dated_dir(output_dir, "raw", snapshot.item_set_id)
        write_snapshot(directory, snapshot, "raw")
        typer.echo(directory)


@app.command()
def validate(
    directory: Annotated[
        Path | None,
        typer.Argument(
            help="Read this snapshot directory without Omeka authentication."
        ),
    ] = None,
    item_set_id: Annotated[
        int | None,
        typer.Option(envvar="ITEM_SET_ID", help="Item set ID for live validation."),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(
            envvar="OMEKA_URL",
            help="Omeka URL for live validation or fallback CSV edit links.",
        ),
    ] = None,
    key_identity: Annotated[
        str | None,
        typer.Option(
            envvar="KEY_IDENTITY", help="Omeka key identity for live validation."
        ),
    ] = None,
    key_credential: Annotated[
        str | None,
        typer.Option(
            envvar="KEY_CREDENTIAL", help="Omeka credential for live validation."
        ),
    ] = None,
    check_uris: bool = False,
    check_redirects: Annotated[
        bool,
        typer.Option(
            help="Warn about redirects to another domain. Requires --check-uris."
        ),
    ] = False,
    uri_check_severity: Annotated[
        Severity,
        typer.Option(help="Severity for failed URI checks. Requires --check-uris."),
    ] = Severity.warning,
    output: Path | None = None,
    export_csv: bool = False,
    csv_output: Path = Path("validation_reports"),
    vocabularies: Path | None = None,
) -> None:
    """Validate a snapshot or a live item set."""
    with command_errors():
        if directory is None:
            with connect(base_url, key_identity, key_credential) as api:
                snapshot = capture_snapshot(api, target(item_set_id))
        else:
            snapshot = read_snapshot(directory)
        vocabulary = (
            VocabularyLoader(vocabularies) if vocabularies else VocabularyLoader()
        )
        result = validate_records(snapshot.items, snapshot.media, vocabulary)
        if check_uris:
            asyncio.run(
                check_links(
                    records(snapshot),
                    result,
                    check_redirects=check_redirects,
                    severity=uri_check_severity.value,
                )
            )
        print_report(result)
        if output:
            save_report(result, output)
        if export_csv:
            export_validation_csv(result, snapshot.source or base_url or "", csv_output)
        if result.errors:
            raise typer.Exit(1)


@app.command()
def transform(
    directory: Path,
    output_dir: Path = Path("data"),
    whitespace_only: bool = False,
    vocabularies: Path | None = None,
) -> None:
    """Write a new snapshot with deterministic cleanup."""
    from .changes import changed_fields

    with command_errors():
        source = read_snapshot(directory)
        vocabulary = (
            VocabularyLoader(vocabularies) if vocabularies else VocabularyLoader()
        )
        item_set, items, media = transform_item_set_data(
            source.item_set or {},
            source.items,
            source.media,
            apply_all=not whitespace_only,
            allowed_mime_types=vocabulary.mime_types,
        )
        edited = Snapshot(source.source, item_set, items, media)
        for kind, pairs in (
            ("item_sets", [(source.item_set or {}, edited.item_set or {})]),
            ("items", zip(source.items, edited.items, strict=True)),
            ("media", zip(source.media, edited.media, strict=True)),
        ):
            for before, after in pairs:
                fields = changed_fields(before, after)
                if fields:
                    typer.echo(f"{kind}/{before.get('o:id')}  {', '.join(fields)}")
        destination = dated_dir(output_dir, "transformed", source.item_set_id)
        write_snapshot(destination, edited, "transformed", source_directory=directory)
        typer.echo(destination)


def plan_snapshot_update(
    source: Snapshot, edited: Snapshot
) -> Iterator[tuple[str, Record, Record]]:
    if source.item_set_id != edited.item_set_id or source.source != edited.source:
        raise ValueError("The edited snapshot must describe the same source item set")
    for kind, left, right in (
        ("item_sets", [source.item_set or {}], [edited.item_set or {}]),
        ("items", source.items, edited.items),
        ("media", source.media, edited.media),
    ):
        if left == right:
            continue
        original = {record["o:id"]: record for record in left}
        updated = {record["o:id"]: record for record in right}
        if len(original) != len(left) or len(updated) != len(right):
            raise ValueError(f"Duplicate {kind} IDs in snapshot")
        if original.keys() != updated.keys():
            raise ValueError(
                f"Use create for new {kind}; keep all source records in the edit"
            )
        for rid, before in original.items():
            yield kind, before, updated[rid]


@app.command()
def update(
    source: Path,
    edited: Path,
    item_set_id: ItemSetID = None,
    base_url: BaseURL = None,
    key_identity: Identity = None,
    key_credential: Credential = None,
    apply: bool = False,
    backup_dir: Path = Path("backups"),
    skip_recent_hours: float = 2,
    exclusive_write: ExclusiveWrite = False,
) -> None:
    """Compare two snapshots and apply changes when requested."""
    from .writes import require_exclusive_write, update_record

    with command_errors():
        require_exclusive_write(apply, exclusive_write)
        baseline = read_snapshot(source)
        proposed = read_snapshot(edited)
        if item_set_id is not None and baseline.item_set_id != item_set_id:
            raise ValueError("The selected item set differs from the source snapshot")
        plan = list(plan_snapshot_update(baseline, proposed))
        with connect(base_url or baseline.source, key_identity, key_credential) as api:
            if not baseline.source or api.installation_url != baseline.source:
                raise ValueError(
                    "The update target must match the source snapshot instance"
                )
            failures = 0
            copies = dated_dir(backup_dir, "before_edit", baseline.item_set_id)
            for kind, before, after in plan:
                label = f"{kind}/{before['o:id']}"
                try:
                    result = update_record(
                        api,
                        kind,
                        before,
                        after,
                        apply=apply,
                        backup_dir=copies,
                        skip_recent_hours=skip_recent_hours,
                        exclusive_write=exclusive_write,
                    )
                except (OmekaError, OSError, ValueError) as exc:
                    typer.echo(f"{label} skipped or failed: {exc}", err=True)
                    failures += 1
                else:
                    if result.status == "unchanged":
                        continue
                    action = {
                        "preview": "Would change",
                        "updated": "Verified",
                        "already_applied": "Already applied",
                    }[result.status]
                    typer.echo(f"{action} {label}  {', '.join(result.fields)}")
            if failures:
                typer.echo(f"{failures} record changes skipped or failed", err=True)
                raise typer.Exit(1)


create_app = typer.Typer(no_args_is_help=True)
app.add_typer(create_app, name="create")


@create_app.command("item")
def create_item(
    json_file: Path,
    item_set_id: ItemSetID = None,
    base_url: BaseURL = None,
    key_identity: Identity = None,
    key_credential: Credential = None,
    apply: bool = False,
) -> None:
    """Create an item from Omeka JSON."""
    from .snapshots import read_json
    from .writes import create_record

    with command_errors(), connect(base_url, key_identity, key_credential) as api:
        record = create_record(
            api,
            "items",
            read_json(json_file),
            target_id=target(item_set_id),
            apply=apply,
        )
        show_creation(record, apply)


@create_app.command("media")
def create_media(
    json_file: Path,
    item_id: int | None = None,
    file: Path | None = None,
    base_url: BaseURL = None,
    key_identity: Identity = None,
    key_credential: Credential = None,
    apply: bool = False,
) -> None:
    """Attach media from Omeka JSON and an optional local file."""
    from .snapshots import read_json
    from .writes import create_record

    with command_errors(), connect(base_url, key_identity, key_credential) as api:
        record = create_record(
            api,
            "media",
            read_json(json_file),
            target_id=item_id,
            file=file,
            apply=apply,
        )
        show_creation(record, apply)


def show_creation(record: dict, apply: bool) -> None:
    if apply:
        typer.echo(f"Created and verified {record.get('@id', record['o:id'])}")
    else:
        typer.echo(f"Would create a record with fields: {', '.join(sorted(record))}")


@app.command("backup")
def backup_command(
    item_set_id: ItemSetID = None,
    base_url: BaseURL = None,
    key_identity: Identity = None,
    key_credential: Credential = None,
    output_dir: Path = Path("backups"),
) -> None:
    """Back up an item set and verify its original files."""
    from .recovery import backup

    with command_errors(), connect(base_url, key_identity, key_credential) as api:
        rid = target(item_set_id)
        directory = dated_dir(output_dir, "backup", rid)
        manifest = backup(api, rid, directory)
        typer.echo(directory)
        if not manifest["complete"]:
            typer.echo("\n".join(manifest["errors"]), err=True)
            raise typer.Exit(1)


@app.command("restore")
def restore_command(
    directory: Path,
    key_identity: Identity = None,
    key_credential: Credential = None,
    apply: bool = False,
    skip_recent_hours: float = 2,
    exclusive_write: ExclusiveWrite = False,
) -> None:
    """Preview or apply recovery on the source instance."""
    from .recovery import backup_source, restore
    from .writes import require_exclusive_write

    with command_errors():
        require_exclusive_write(apply, exclusive_write)
        source = backup_source(directory)
        with connect(source, key_identity, key_credential) as api:
            restore(
                api,
                directory,
                apply=apply,
                skip_recent_hours=skip_recent_hours,
                announce=typer.echo,
                exclusive_write=exclusive_write,
            )


def main() -> None:
    load_dotenv(Path.cwd() / ".env")
    app()
