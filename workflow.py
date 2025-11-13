"""
SGB Data Workflow CLI

Unified CLI for downloading, transforming, validating, and uploading Omeka S data.

Commands:
- download  Download raw data (no transformations) from Omeka S
- transform Apply transformations to previously downloaded raw data
- validate  Validate offline JSON files (raw or transformed)
- upload    Upload transformed data back to Omeka S

Notes:
- Raw files are saved with *_raw.json
- Transformed files are saved with *_transformed.json
"""

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from src.api import OmekaAPI

# Load environment variables
load_dotenv()

# Create the main Typer app
app = typer.Typer(
    help="SGB data workflow: download, transform, validate, upload",
    no_args_is_help=True,
)


@app.command()
def download(
    item_set_id: Annotated[
        int,
        typer.Option(
            help="Item set ID to download",
        ),
    ],
    base_url: Annotated[
        str | None,
        typer.Option(
            help="Base URL of the Omeka S instance",
            envvar="OMEKA_URL",
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Output directory for raw data",
        ),
    ] = Path("data"),
    key_identity: Annotated[
        str | None,
        typer.Option(
            help="API key identity for authentication (optional)",
            envvar="KEY_IDENTITY",
        ),
    ] = None,
    key_credential: Annotated[
        str | None,
        typer.Option(
            help="API key credential for authentication (optional)",
            envvar="KEY_CREDENTIAL",
        ),
    ] = None,
) -> None:
    """Download raw data from Omeka S (no transformations)."""
    typer.echo("=" * 80)
    typer.echo("DOWNLOAD DATA")
    typer.echo("=" * 80)

    if not base_url:
        typer.echo(
            "✗ Error: Base URL not provided. Use --base-url or set OMEKA_URL in .env",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"Base URL: {base_url}")
    typer.echo(f"Item Set ID: {item_set_id}")
    typer.echo(f"Output directory: {output}")
    typer.echo()

    with OmekaAPI(
        base_url,
        key_identity=key_identity,
        key_credential=key_credential,
    ) as api:
        result = api.download_item_set(
            item_set_id=item_set_id,
            output_dir=output,
        )

        typer.echo(f"✓ Downloaded {result['items_downloaded']} items")
        typer.echo(f"✓ Downloaded {result['media_downloaded']} media")

        if result["saved_to"]:
            typer.echo()
            directory = result["saved_to"]["directory"]
            typer.echo(f"Saved to: {directory}")
            typer.echo()
            typer.echo("Next steps:")
            typer.echo(f"  python workflow.py transform {directory}")
            typer.echo(f"  python workflow.py validate {directory}")


@app.command()
def transform(
    input_dir: Annotated[
        Path,
        typer.Argument(
            help="Directory containing raw data files to transform",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            help="Output directory for transformed data (default: auto)",
        ),
    ] = None,
    no_transformations: Annotated[
        bool,
        typer.Option(
            help="Skip all transformations (no changes to data)",
        ),
    ] = False,
) -> None:
    """Apply transformations to downloaded data."""
    typer.echo("=" * 80)
    typer.echo("TRANSFORM DATA")
    typer.echo("=" * 80)
    typer.echo(f"Input directory: {input_dir}")
    typer.echo(f"Output directory: {output or 'same as input parent'}")
    apply_transforms = not no_transformations
    typer.echo(f"Apply transformations: {apply_transforms}")
    typer.echo()

    # Base URL not needed for transformation, but API needs it
    with OmekaAPI("https://omeka.unibe.ch") as api:
        result = api.apply_transformations(
            input_dir=input_dir,
            output_dir=output,
            apply_whitespace_normalization=apply_transforms,
            apply_all_transformations=apply_transforms,
            upgrade_https=apply_transforms,
        )

        typer.echo(f"✓ Transformed {result['items_transformed']} items")
        typer.echo(f"✓ Transformed {result['media_transformed']} media")
        transformations = ", ".join(result["transformations_applied"]) or "(none)"
        typer.echo(f"✓ Transformations applied: {transformations}")

        if result["saved_to"]:
            typer.echo()
            typer.echo("Transformed data saved to:")
            typer.echo(f"  Directory: {result['saved_to']['directory']}")
            typer.echo(f"  Items: {result['saved_to']['items']}")
            typer.echo(f"  Media: {result['saved_to']['media']}")
            typer.echo()
            typer.echo("Next steps:")
            directory = result["saved_to"]["directory"]
            typer.echo(f"  To validate: python workflow.py validate {directory}")
            typer.echo(f"  To upload: python workflow.py upload {directory}")


@app.command()
def validate(
    directory: Annotated[
        Path,
        typer.Argument(
            help="Directory containing the JSON files to validate",
        ),
    ],
) -> None:
    """Validate offline JSON files."""
    typer.echo("=" * 80)
    typer.echo("VALIDATE OFFLINE FILES")
    typer.echo("=" * 80)
    typer.echo(f"Directory: {directory}")
    typer.echo()

    # Base URL not needed for offline validation, but API needs it
    with OmekaAPI("https://omeka.unibe.ch") as api:
        result = api.validate_offline_files(directory)

        typer.echo(f"Items validated: {result['items_validated']}")
        typer.echo(f"Items valid: {result['items_valid']}")
        if result["items_errors"]:
            typer.echo(f"Items with errors: {len(result['items_errors'])}")

        typer.echo()
        typer.echo(f"Media validated: {result['media_validated']}")
        typer.echo(f"Media valid: {result['media_valid']}")
        if result["media_errors"]:
            typer.echo(f"Media with errors: {len(result['media_errors'])}")

        if result["overall_valid"]:
            typer.echo()
            typer.echo("✓ All files are valid and ready for upload")
        else:
            typer.echo()
            typer.echo("✗ Validation errors found:")
            for item_error in result["items_errors"]:
                typer.echo(f"  Item {item_error['item_id']}:")
                for error in item_error["errors"]:
                    typer.echo(f"    - {error}")
            for media_error in result["media_errors"]:
                typer.echo(f"  Media {media_error['media_id']}:")
                for error in media_error["errors"]:
                    typer.echo(f"    - {error}")
            raise typer.Exit(1)


@app.command()
def upload(
    directory: Annotated[
        Path,
        typer.Argument(
            help="Directory containing the JSON files to upload",
        ),
    ],
    base_url: Annotated[
        str | None,
        typer.Option(
            help="Base URL of the Omeka S instance",
            envvar="OMEKA_URL",
        ),
    ] = None,
    key_identity: Annotated[
        str | None,
        typer.Option(
            help="API key identity for authentication (required for upload)",
            envvar="KEY_IDENTITY",
        ),
    ] = None,
    key_credential: Annotated[
        str | None,
        typer.Option(
            help="API key credential for authentication (required for upload)",
            envvar="KEY_CREDENTIAL",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            help="Validate only, do not upload (default: True)",
        ),
    ] = True,
    no_dry_run: Annotated[
        bool,
        typer.Option(
            "--no-dry-run",
            help="Actually upload the data (use with caution!)",
        ),
    ] = False,
) -> None:
    """Upload transformed data back to Omeka S."""
    typer.echo("=" * 80)
    typer.echo("UPLOAD TRANSFORMED DATA")
    typer.echo("=" * 80)

    # Handle dry_run flag
    if no_dry_run:
        dry_run = False

    if not base_url:
        typer.echo(
            "✗ Error: Base URL not provided. Use --base-url or set OMEKA_URL in .env",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"Base URL: {base_url}")
    typer.echo(f"Directory: {directory}")
    typer.echo(f"Dry run: {dry_run}")
    typer.echo()

    if dry_run:
        typer.echo("⚠ DRY RUN MODE - No changes will be made")
        typer.echo()

    if not key_identity or not key_credential:
        typer.echo(
            "✗ Error: API credentials required for upload",
            err=True,
        )
        typer.echo("  Provide --key-identity, --key-credential", err=True)
        typer.echo("  Or set KEY_IDENTITY, KEY_CREDENTIAL in .env", err=True)
        raise typer.Exit(1)

    with OmekaAPI(
        base_url,
        key_identity=key_identity,
        key_credential=key_credential,
    ) as api:
        result = api.upload_transformed_data(
            directory=directory,
            dry_run=dry_run,
        )

        typer.echo(f"Items processed: {result['items_processed']}")
        typer.echo(f"Items updated: {result['items_updated']}")
        typer.echo(f"Items failed: {result['items_failed']}")
        typer.echo()
        typer.echo(f"Media processed: {result['media_processed']}")
        typer.echo(f"Media updated: {result['media_updated']}")
        typer.echo(f"Media failed: {result['media_failed']}")

        # Show pre-validation summary if available
        pre = result.get("pre_validation")
        if pre:
            typer.echo()
            typer.echo("Pre-validation summary (non-blocking):")
            typer.echo(
                f"  Items: {pre['items_valid']}/{pre['items_validated']} valid; "
                f"Errors: {pre['items_errors_count']}"
            )
            typer.echo(
                f"  Media: {pre['media_valid']}/{pre['media_validated']} valid; "
                f"Errors: {pre['media_errors_count']}"
            )

        if result["errors"]:
            typer.echo()
            typer.echo("Warnings/Errors:")
            for error in result["errors"]:
                error_type = error.get("type", "unknown")
                error_msg = error.get("message", "Unknown error")
                typer.echo(f"  {error_type}: {error_msg}")

        if dry_run:
            typer.echo()
            typer.echo("✓ Dry run completed - no changes were made")
            typer.echo("  To actually upload, run again with --no-dry-run")
        elif (
            result["items_failed"] == 0
            and result["media_failed"] == 0
            and not result["errors"]
        ):
            typer.echo()
            typer.echo("✓ Upload completed successfully")
        else:
            typer.echo()
            typer.echo("✗ Upload completed with errors")
            raise typer.Exit(1)


@app.command()
def pipeline(
    item_set_id: Annotated[
        int,
        typer.Option(
            help="Item set ID to process",
        ),
    ],
    base_url: Annotated[
        str | None,
        typer.Option(
            help="Base URL of Omeka S",
            envvar="OMEKA_URL",
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option(
            help="Root output directory",
        ),
    ] = Path("data"),
    key_identity: Annotated[
        str | None,
        typer.Option(
            help="API key identity (required for upload stage)",
            envvar="KEY_IDENTITY",
        ),
    ] = None,
    key_credential: Annotated[
        str | None,
        typer.Option(
            help="API key credential (required for upload stage)",
            envvar="KEY_CREDENTIAL",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            help="Dry run upload (default: enabled)",
        ),
    ] = True,
    no_dry_run: Annotated[
        bool,
        typer.Option(
            "--no-dry-run",
            help="Perform real upload",
        ),
    ] = False,
    skip_validate: Annotated[
        bool,
        typer.Option(
            help="Skip validation before upload",
        ),
    ] = False,
    force_upload: Annotated[
        bool,
        typer.Option(
            help="Proceed with upload even if validation finds errors",
        ),
    ] = False,
) -> None:
    """Run download → transform → validate → upload in one step."""
    typer.echo("=" * 80)
    typer.echo("PIPELINE RUN")
    typer.echo("=" * 80)

    if not base_url:
        typer.echo(
            "✗ Error: Base URL not provided. Use --base-url or set OMEKA_URL in .env",
            err=True,
        )
        raise typer.Exit(1)

    # Handle dry_run flag
    if no_dry_run:
        dry_run = False

    typer.echo(f"Base URL: {base_url}")
    typer.echo(f"Item Set ID: {item_set_id}")
    typer.echo(f"Output root: {output}")
    typer.echo(f"Dry run: {dry_run}")
    typer.echo(f"Skip validate: {skip_validate}")
    typer.echo(f"Force upload on validation errors: {force_upload}")
    typer.echo()

    with OmekaAPI(
        base_url, key_identity=key_identity, key_credential=key_credential
    ) as api:
        typer.echo("[1/4] Downloading raw data...")
        download_result = api.download_item_set(
            item_set_id=item_set_id, output_dir=output
        )
        raw_dir = download_result["saved_to"]["directory"]
        typer.echo(f"✓ Raw data saved to {raw_dir}")
        typer.echo(
            f"  Items: {download_result['items_downloaded']} | Media: {download_result['media_downloaded']}"
        )
        typer.echo()

        typer.echo("[2/4] Applying transformations...")
        transform_result = api.apply_transformations(input_dir=raw_dir)
        transformed_dir = transform_result["saved_to"]["directory"]
        typer.echo(f"✓ Transformed data saved to {transformed_dir}")
        typer.echo(
            f"  Items transformed: {transform_result['items_transformed']} | Media transformed: {transform_result['media_transformed']}"
        )
        typer.echo(
            f"  Transformations: {', '.join(transform_result['transformations_applied']) or '(none)'}"
        )
        typer.echo()

        validation_ok = True
        if not skip_validate:
            typer.echo("[3/4] Validating transformed data...")
            validation_result = api.validate_offline_files(transformed_dir)
            validation_ok = validation_result["overall_valid"]
            typer.echo(
                "  Items valid: "
                + f"{validation_result['items_valid']}/{validation_result['items_validated']}"
            )
            typer.echo(
                "  Media valid: "
                + f"{validation_result['media_valid']}/{validation_result['media_validated']}"
            )
            if not validation_ok:
                typer.echo(
                    "  ✗ Validation found errors (upload will be skipped unless --force-upload)"
                )
            else:
                typer.echo("  ✓ Validation passed")
            typer.echo()
        else:
            typer.echo("[3/4] Validation skipped (--skip-validate)")
            typer.echo()

        do_upload = validation_ok or force_upload or skip_validate
        if not do_upload:
            typer.echo(
                "[4/4] Upload skipped due to validation errors. Use --force-upload to override."
            )
            raise typer.Exit(1)
        if not key_identity or not key_credential:
            typer.echo(
                "[4/4] Upload skipped: missing API credentials (KEY_IDENTITY / KEY_CREDENTIAL)"
            )
            raise typer.Exit(1)

        typer.echo("[4/4] Uploading transformed data (dry_run=" + str(dry_run) + ")...")
        upload_result = api.upload_transformed_data(
            directory=transformed_dir, dry_run=dry_run
        )
        typer.echo(
            f"  Items processed: {upload_result['items_processed']}, updated: {upload_result['items_updated']}, failed: {upload_result['items_failed']}"
        )
        typer.echo(
            f"  Media processed: {upload_result['media_processed']}, updated: {upload_result['media_updated']}, failed: {upload_result['media_failed']}"
        )
        if upload_result["errors"]:
            typer.echo("  Warnings/Errors:")
            for err in upload_result["errors"]:
                t = err.get("type", "unknown")
                msg = err.get("message", "Unknown error")
                typer.echo(f"    - {t}: {msg}")

        if dry_run:
            typer.echo(
                "\n✓ Pipeline completed (dry-run). Re-run with --no-dry-run to apply changes."
            )
        else:
            if (
                upload_result["items_failed"] == 0
                and upload_result["media_failed"] == 0
            ):
                typer.echo("\n✓ Pipeline completed successfully.")
            else:
                typer.echo("\n✗ Pipeline completed with some upload failures.")

        success = dry_run or (
            upload_result["items_failed"] == 0 and upload_result["media_failed"] == 0
        )
        if not success:
            raise typer.Exit(1)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
