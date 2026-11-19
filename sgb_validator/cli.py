"""The sgb command-line interface."""

import asyncio
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from .api import OmekaAPI, OmekaError
from .links import check_links
from .reports import export_validation_csv, print_report, save_report
from .snapshots import Snapshot, download_snapshot, read_snapshot, write_snapshot
from .transformations import transform_item_set_data
from .validation import validate_records
from .vocabularies import VocabularyLoader

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
BaseURL = Annotated[str | None, typer.Option("--base-url", envvar="OMEKA_URL")]
ItemSetID = Annotated[int | None, typer.Option(envvar="ITEM_SET_ID")]
Identity = Annotated[str | None, typer.Option(envvar="KEY_IDENTITY")]
Credential = Annotated[str | None, typer.Option(envvar="KEY_CREDENTIAL")]


class Severity(str, Enum):
    warning = "warning"
    error = "error"


@contextmanager
def command_errors():
    try:
        yield
    except (OmekaError, OSError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None


def connect(
    base_url: str | None, identity: str | None, credential: str | None
) -> OmekaAPI:
    if not base_url:
        raise ValueError("Set OMEKA_URL or pass --base-url")
    return OmekaAPI(base_url, identity, credential)


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
        snapshot = download_snapshot(api, target(item_set_id))
        directory = dated_dir(output_dir, "raw", snapshot.item_set_id)
        write_snapshot(directory, snapshot, "raw")
        typer.echo(directory)


@app.command()
def validate(
    directory: Annotated[Path | None, typer.Argument()] = None,
    item_set_id: ItemSetID = None,
    base_url: BaseURL = None,
    key_identity: Identity = None,
    key_credential: Credential = None,
    check_uris: bool = False,
    check_redirects: bool = False,
    uri_check_severity: Severity = Severity.warning,
    output: Path | None = None,
    export_csv: bool = False,
    csv_output: Path = Path("validation_reports"),
    vocabularies: Path | None = None,
) -> None:
    """Validate a snapshot or a live item set."""
    with command_errors():
        if directory is None:
            with connect(base_url, key_identity, key_credential) as api:
                snapshot = download_snapshot(api, target(item_set_id))
        else:
            snapshot = read_snapshot(directory)
        vocabulary = (
            VocabularyLoader(vocabularies) if vocabularies else VocabularyLoader()
        )
        result = validate_records(snapshot.items, snapshot.media, vocabulary)
        if check_uris:
            asyncio.run(
                check_links(
                    snapshot.records(),
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
            source.item_set,
            source.items,
            source.media,
            apply_all=not whitespace_only,
            allowed_mime_types=vocabulary.mime_types,
        )
        edited = Snapshot(item_set, items, media, source.source)
        for kind, pairs in (
            ("item_sets", [(source.item_set, edited.item_set)]),
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


def main() -> None:
    load_dotenv(Path.cwd() / ".env")
    app()
