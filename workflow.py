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

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.api import OmekaAPI

# Load environment variables
load_dotenv()


def download_data(args: argparse.Namespace) -> int:
    """Download raw data from Omeka without applying transformations."""
    print("=" * 80)
    print("DOWNLOAD DATA")
    print("=" * 80)
    base_url = args.base_url or os.getenv("OMEKA_URL")
    if not base_url:
        print("✗ Error: Base URL not provided. Use --base-url or set OMEKA_URL in .env")
        return 1
    print(f"Base URL: {base_url}")
    print(f"Item Set ID: {args.item_set_id}")
    print(f"Output directory: {args.output}")
    print()

    # Credentials optional for download; pull from env if not provided
    key_identity = args.key_identity or os.getenv("KEY_IDENTITY")
    key_credential = args.key_credential or os.getenv("KEY_CREDENTIAL")

    with OmekaAPI(
        base_url,
        key_identity=key_identity,
        key_credential=key_credential,
    ) as api:
        result = api.download_item_set(
            item_set_id=args.item_set_id,
            output_dir=args.output,
        )

        print(f"✓ Downloaded {result['items_downloaded']} items (raw)")
        print(f"✓ Downloaded {result['media_downloaded']} media (raw)")

        if result["saved_to"]:
            print()
            print("Raw data saved to:")
            print(f"  Directory: {result['saved_to']['directory']}")
            print(f"  Items (raw): {result['saved_to']['items']}")
            print(f"  Media (raw): {result['saved_to']['media']}")
            print(f"  Metadata: {result['saved_to']['metadata']}")
            print()
            print("Next steps:")
            directory = result["saved_to"]["directory"]
            print(f"  To transform: python workflow.py transform {directory}")
            print(f"  To validate: python workflow.py validate {directory}")

    return 0


def transform_data(args: argparse.Namespace) -> int:
    """Apply transformations to previously downloaded raw data."""
    print("=" * 80)
    print("TRANSFORM DATA")
    print("=" * 80)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output or 'same as input parent'}")
    all_transforms = not args.no_all_transformations
    print(f"Apply all transformations: {all_transforms}")
    if all_transforms:
        https_status = "enabled" if args.https_upgrade else "disabled"
        print(f"HTTPS upgrade: {https_status}")
    print()

    with OmekaAPI(
        args.base_url or os.getenv("OMEKA_URL") or "https://omeka.unibe.ch"
    ) as api:
        result = api.apply_transformations(
            input_dir=args.input_dir,
            output_dir=args.output,
            apply_whitespace_normalization=not args.no_whitespace_normalization,
            apply_all_transformations=not args.no_all_transformations,
            upgrade_https=args.https_upgrade,
        )

        print(f"✓ Transformed {result['items_transformed']} items (transformed)")
        print(f"✓ Transformed {result['media_transformed']} media (transformed)")
        transformations = ", ".join(result["transformations_applied"]) or "(none)"
        print(f"✓ Transformations applied: {transformations}")

        if result["saved_to"]:
            print()
            print("Transformed data saved to:")
            print(f"  Directory: {result['saved_to']['directory']}")
            print(f"  Items (transformed): {result['saved_to']['items']}")
            print(f"  Media (transformed): {result['saved_to']['media']}")
            print(f"  Metadata: {result['saved_to']['metadata']}")
            print()
            print("Next steps:")
            directory = result["saved_to"]["directory"]
            print(f"  To validate: python workflow.py validate {directory}")
            print(
                f"  To upload: python workflow.py upload {directory} "
                f"--base-url {args.base_url or 'https://omeka.unibe.ch'}"
            )

    return 0


def validate_offline(args: argparse.Namespace) -> int:
    """Validate offline JSON files."""
    print("=" * 80)
    print("VALIDATE OFFLINE FILES")
    print("=" * 80)
    print(f"Directory: {args.directory}")
    print()

    with OmekaAPI(args.base_url or "https://omeka.unibe.ch") as api:
        result = api.validate_offline_files(args.directory)

        print(f"Items validated: {result['items_validated']}")
        print(f"Items valid: {result['items_valid']}")
        if result["items_errors"]:
            print(f"Items with errors: {len(result['items_errors'])}")

        print()
        print(f"Media validated: {result['media_validated']}")
        print(f"Media valid: {result['media_valid']}")
        if result["media_errors"]:
            print(f"Media with errors: {len(result['media_errors'])}")

        if result["overall_valid"]:
            print()
            print("✓ All files are valid and ready for upload")
            return 0
        else:
            print()
            print("✗ Validation errors found:")
            for item_error in result["items_errors"]:
                print(f"  Item {item_error['item_id']}:")
                for error in item_error["errors"]:
                    print(f"    - {error}")
            for media_error in result["media_errors"]:
                print(f"  Media {media_error['media_id']}:")
                for error in media_error["errors"]:
                    print(f"    - {error}")
            return 1


def upload_data(args: argparse.Namespace) -> int:
    """Upload transformed data back to Omeka S."""
    print("=" * 80)
    print("UPLOAD TRANSFORMED DATA")
    print("=" * 80)
    # Determine base URL and credentials (prefer args, fall back to env)
    base_url = args.base_url or os.getenv("OMEKA_URL")
    print(f"Base URL: {base_url}")
    print(f"Directory: {args.directory}")
    print(f"Dry run: {args.dry_run}")
    print()

    if args.dry_run:
        print("⚠ DRY RUN MODE - No changes will be made")
        print()

    env_key_identity = os.getenv("KEY_IDENTITY")
    env_key_credential = os.getenv("KEY_CREDENTIAL")

    key_identity = args.key_identity or env_key_identity
    key_credential = args.key_credential or env_key_credential

    if not key_identity or not key_credential or not base_url:
        print("✗ Error: API credentials and base URL required for upload")
        print("  Provide --base-url, --key-identity, --key-credential")
        print("  Or set OMEKA_URL[_V4], KEY_IDENTITY[_V4], KEY_CREDENTIAL[_V4] in .env")
        return 1

    with OmekaAPI(
        base_url,
        key_identity=key_identity,
        key_credential=key_credential,
    ) as api:
        result = api.upload_transformed_data(
            directory=args.directory,
            dry_run=args.dry_run,
        )

        print(f"Items processed: {result['items_processed']}")
        print(f"Items updated: {result['items_updated']}")
        print(f"Items failed: {result['items_failed']}")
        print()
        print(f"Media processed: {result['media_processed']}")
        print(f"Media updated: {result['media_updated']}")
        print(f"Media failed: {result['media_failed']}")

        # Show pre-validation summary if available
        pre = result.get("pre_validation")
        if pre:
            print()
            print("Pre-validation summary (non-blocking):")
            print(
                f"  Items: {pre['items_valid']}/{pre['items_validated']} valid; "
                f"Errors: {pre['items_errors_count']}"
            )
            print(
                f"  Media: {pre['media_valid']}/{pre['media_validated']} valid; "
                f"Errors: {pre['media_errors_count']}"
            )

        if result["errors"]:
            print()
            print("Warnings/Errors:")
            for error in result["errors"]:
                error_type = error.get("type", "unknown")
                error_msg = error.get("message", "Unknown error")
                print(f"  {error_type}: {error_msg}")

        if args.dry_run:
            print()
            print("✓ Dry run completed - no changes were made")
            print("  To actually upload, run again with --no-dry-run")
            return 0
        elif (
            result["items_failed"] == 0
            and result["media_failed"] == 0
            and not result["errors"]
        ):
            print()
            print("✓ Upload completed successfully")
            return 0
        else:
            print()
            print("✗ Upload completed with errors")
            return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SGB data workflow: download, transform, validate, upload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download raw data (no transformations)
  python workflow.py download --item-set-id 10780 --output data/ --base-url https://omeka.unibe.ch

  # Transform downloaded data (defaults to ALL transformations)
  python workflow.py transform data/raw_itemset_10780_20250115/

  # Transform with only whitespace normalization
  python workflow.py transform data/raw_itemset_10780_20250115/ \\
    --no-all-transformations

  # Validate offline files
  python workflow.py validate data/transformed_itemset_10780_20250115/

  # Upload with dry-run (validate only, no changes)
  python workflow.py upload data/transformed_itemset_10780_20250115/ --base-url https://omeka.unibe.ch

  # Upload for real (requires API credentials)
  python workflow.py upload data/transformed_itemset_10780_20250115/ \
    --base-url https://omeka.unibe.ch \
    --key-identity YOUR_KEY \
    --key-credential YOUR_SECRET \
    --no-dry-run

For more information, see the documentation.
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Download command
    download_parser = subparsers.add_parser(
        "download",
        help="Download raw data from Omeka S (no transformations)",
    )
    download_parser.add_argument(
        "--base-url",
        help="Base URL of the Omeka S instance (defaults to $OMEKA_URL)",
    )
    download_parser.add_argument(
        "--item-set-id",
        type=int,
        required=True,
        help="Item set ID to download",
    )
    download_parser.add_argument(
        "--output",
        type=Path,
        default="data",
        help="Output directory for raw data (default: data/)",
    )
    download_parser.add_argument(
        "--key-identity",
        help="API key identity for authentication (optional)",
    )
    download_parser.add_argument(
        "--key-credential",
        help="API key credential for authentication (optional)",
    )

    # Transform command
    transform_parser = subparsers.add_parser(
        "transform",
        help="Apply transformations to downloaded data",
    )
    transform_parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing raw data files to transform",
    )
    transform_parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for transformed data (default: parent of input_dir)",
    )
    transform_parser.add_argument(
        "--base-url",
        help="Base URL (not required for transformation)",
    )
    # Transformation options: default applies ALL transformations with granular opt-outs
    transform_parser.add_argument(
        "--no-all-transformations",
        action="store_true",
        help=(
            "Disable comprehensive transformations (Unicode NFC, HTML entities, "
            "Markdown links, abbreviations, URL normalization). "
            "Only whitespace normalization will be applied unless also disabled."
        ),
    )
    transform_parser.add_argument(
        "--no-whitespace-normalization",
        action="store_true",
        help="Skip whitespace normalization.",
    )
    transform_parser.add_argument(
        "--no-https-upgrade",
        action="store_false",
        dest="https_upgrade",
        help="Disable HTTP→HTTPS upgrade (default: enabled).",
    )
    transform_parser.set_defaults(https_upgrade=True)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate offline JSON files",
    )
    validate_parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing the JSON files to validate",
    )
    validate_parser.add_argument(
        "--base-url",
        help="Base URL (not required for offline validation)",
    )

    # Upload command
    upload_parser = subparsers.add_parser(
        "upload",
        help="Upload transformed data back to Omeka S",
    )
    upload_parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing the JSON files to upload",
    )
    upload_parser.add_argument(
        "--base-url",
        help=("Base URL of the Omeka S instance (defaults to $OMEKA_URL)"),
    )
    upload_parser.add_argument(
        "--key-identity",
        help="API key identity for authentication (required for upload)",
    )
    upload_parser.add_argument(
        "--key-credential",
        help="API key credential for authentication (required for upload)",
    )
    upload_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Validate only, do not upload (default)",
    )
    upload_parser.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="Actually upload the data (use with caution!)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "download":
        return download_data(args)
    elif args.command == "transform":
        return transform_data(args)
    elif args.command == "validate":
        return validate_offline(args)
    elif args.command == "upload":
        return upload_data(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
