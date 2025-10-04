"""
Omeka S data validator for Stadt.Geschichte.Basel project.

This module validates items and media from the Omeka S API against
a comprehensive data model using pydantic.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from src.models import Item, Media
from src.vocabularies import VocabularyLoader


class DataValidationError:
    """Represents a validation error"""

    def __init__(
        self, resource_type: str, resource_id: int, field: str, error: str
    ) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.field = field
        self.error = error

    def __str__(self) -> str:
        return f"[{self.resource_type} {self.resource_id}] {self.field}: {self.error}"


class DataValidationWarning:
    """Represents a validation warning (informational, not an error)"""

    def __init__(self, resource_type: str, resource_id: int, message: str) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.message = message

    def __str__(self) -> str:
        return f"[{self.resource_type} {self.resource_id}] {self.message}"


class OmekaValidator:
    """Validates Omeka S data against data model"""

    def __init__(
        self, base_url: str, api_key: str | None = None, check_uris: bool = False
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.check_uris = check_uris
        self.errors: list[DataValidationError] = []
        self.warnings: list[DataValidationWarning] = []
        self.validated_items = 0
        self.validated_media = 0

        headers = {}
        if api_key:
            headers["key_identity"] = api_key

        self.client = httpx.Client(headers=headers, timeout=30.0)

        vocab_file = Path(__file__).parent / "data" / "raw" / "vocabularies.json"
        self.vocab_loader = VocabularyLoader(vocab_file)

    def fetch_items(self, item_set_id: int) -> list[dict[str, Any]]:
        """Fetch all items from an item set"""
        items: list[dict[str, Any]] = []
        page = 1
        per_page = 50

        while True:
            url = f"{self.base_url}/api/items"
            params = {"item_set_id": item_set_id, "page": page, "per_page": per_page}

            response = self.client.get(url, params=params)
            response.raise_for_status()

            page_items = response.json()
            if not page_items:
                break

            items.extend(page_items)
            page += 1

        return items

    def fetch_media(self, item_id: int) -> list[dict[str, Any]]:
        """Fetch all media for an item"""
        url = f"{self.base_url}/api/media"
        params = {"item_id": item_id}
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def validate_item(self, item_data: dict[str, Any]) -> None:
        """Validate a single item"""
        try:
            Item.model_validate(item_data)
            self.validated_items += 1
        except ValidationError as e:
            item_id = item_data.get("o:id", "unknown")
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                self.errors.append(
                    DataValidationError("Item", item_id, field, error["msg"])
                )

    def validate_media(self, media_data: dict[str, Any]) -> None:
        """Validate a single media object"""
        try:
            Media.model_validate(media_data)
            self.validated_media += 1
        except ValidationError as e:
            media_id = media_data.get("o:id", "unknown")
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                self.errors.append(
                    DataValidationError("Media", media_id, field, error["msg"])
                )

    def validate_item_set(self, item_set_id: int) -> None:
        """Validate all items and media in an item set"""
        print(f"Fetching items from item set {item_set_id}...")
        items = self.fetch_items(item_set_id)
        print(f"Found {len(items)} items")

        for idx, item in enumerate(items, 1):
            print(f"Validating item {idx}/{len(items)}...", end="\r")
            self.validate_item(item)

            # Validate associated media
            item_id = item.get("o:id")
            if item_id:
                try:
                    media_list = self.fetch_media(item_id)
                    if not media_list:
                        # Item has no media - add as informational warning
                        self.warnings.append(
                            DataValidationWarning(
                                "Item", item_id, "No media/children found for this item"
                            )
                        )
                    for media in media_list:
                        self.validate_media(media)
                except httpx.HTTPError as e:
                    print(f"\nWarning: Could not fetch media for item {item_id}: {e}")

        print()  # New line after progress

    def print_report(self) -> None:
        """Print validation report"""
        print("\n" + "=" * 80)
        print("VALIDATION REPORT")
        print("=" * 80)
        print(f"Items validated: {self.validated_items}")
        print(f"Media validated: {self.validated_media}")
        print(f"Total errors: {len(self.errors)}")
        print(f"Total warnings: {len(self.warnings)}")
        print("=" * 80)

        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print("\nWARNINGS (informational):")
            for warning in self.warnings:
                print(f"  {warning}")

    def save_report(self, output_file: Path) -> None:
        """Save validation report to file"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("VALIDATION REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Items validated: {self.validated_items}\n")
            f.write(f"Media validated: {self.validated_media}\n")
            f.write(f"Total errors: {len(self.errors)}\n")
            f.write(f"Total warnings: {len(self.warnings)}\n")
            f.write("=" * 80 + "\n\n")

            if self.errors:
                f.write("ERRORS:\n")
                for error in self.errors:
                    f.write(f"  {error}\n")

            if self.warnings:
                f.write("\nWARNINGS (informational):\n")
                for warning in self.warnings:
                    f.write(f"  {warning}\n")

        print(f"\nReport saved to: {output_file}")


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate Omeka S data against Stadt.Geschichte.Basel data model"
    )
    parser.add_argument(
        "--base-url",
        default="https://omeka.unibe.ch",
        help="Base URL of the Omeka S instance (default: https://omeka.unibe.ch)",
    )
    parser.add_argument(
        "--item-set-id",
        type=int,
        default=10780,
        help="Item set ID to validate (default: 10780)",
    )
    parser.add_argument("--api-key", help="Optional API key for authentication")
    parser.add_argument(
        "--check-uris",
        action="store_true",
        help="Check if URIs are reachable (may be slow)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save report to file (default: print to console only)",
    )

    args = parser.parse_args()

    print("Stadt.Geschichte.Basel Data Validator")
    print(f"Base URL: {args.base_url}")
    print(f"Item Set ID: {args.item_set_id}")
    print()

    validator = OmekaValidator(args.base_url, args.api_key, args.check_uris)

    try:
        validator.validate_item_set(args.item_set_id)
    except httpx.HTTPError as e:
        print(f"Error accessing API: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    validator.print_report()

    if args.output:
        validator.save_report(args.output)

    return 0 if not validator.errors else 1


if __name__ == "__main__":
    sys.exit(main())
