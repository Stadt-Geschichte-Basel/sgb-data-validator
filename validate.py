"""
Omeka S data validator for Stadt.Geschichte.Basel project.

This module validates items and media from the Omeka S API against
a comprehensive data model using pydantic.
"""

import argparse
import asyncio
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
        self,
        base_url: str,
        api_key: str | None = None,
        check_uris: bool = False,
        check_redirects: bool = False,
        uri_check_severity: str = "warning",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.check_uris = check_uris
        self.check_redirects = check_redirects
        self.uri_check_severity = uri_check_severity
        self.errors: list[DataValidationError] = []
        self.warnings: list[DataValidationWarning] = []
        self.validated_items = 0
        self.validated_media = 0
        self.checked_uris = 0
        self.failed_uris = 0
        self.uri_cache: dict[str, tuple[int, str | None]] = {}  # LRU cache for URI checks

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

    async def check_single_uri(self, uri: str) -> tuple[int, str | None]:
        """Check a single URI and return (status_code, redirect_location)"""
        # Check cache first
        if uri in self.uri_cache:
            return self.uri_cache[uri]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False, headers=headers) as client:
            try:
                response = await client.head(uri)
                redirect_location = response.headers.get("location")
                result = (response.status_code, redirect_location)
                # Cache the result
                self.uri_cache[uri] = result
                return result
            except (httpx.RequestError, httpx.HTTPError) as e:
                # Return a special status code for exceptions
                result = (-1, str(e))
                self.uri_cache[uri] = result
                return result

    async def check_uri_async(
        self, uri: str, resource_type: str, resource_id: int, field: str
    ) -> None:
        """Check if a URI is reachable asynchronously"""
        if not uri or not uri.startswith(("http://", "https://")):
            return

        self.checked_uris += 1
        # Truncate long URIs for display
        display_uri = uri if len(uri) <= 60 else uri[:57] + "..."
        print(f"\rChecking URI ({self.checked_uris}): {display_uri}        ", end="", flush=True)
        
        try:
            status_code, redirect_location = await self.check_single_uri(uri)
            
            if status_code == -1:
                # This was an exception
                self.failed_uris += 1
                message = f"URI check failed: {uri} ({redirect_location})"
                if self.uri_check_severity == "error":
                    self.errors.append(
                        DataValidationError(resource_type, resource_id, field, message)
                    )
                else:
                    self.warnings.append(
                        DataValidationWarning(resource_type, resource_id, f"{field}: {message}")
                    )
                return

            # Check for redirects
            if self.check_redirects and status_code in (301, 302, 303, 307, 308):
                # Check if redirect is to a different domain
                if redirect_location and not redirect_location.startswith(uri.split("/")[2]):
                    message = f"URI redirects to different domain: {uri} -> {redirect_location}"
                    self.warnings.append(
                        DataValidationWarning(resource_type, resource_id, f"{field}: {message}")
                    )

            # Check for HTTP errors
            if status_code >= 400:
                self.failed_uris += 1
                message = f"URI returned HTTP {status_code}: {uri}"
                if self.uri_check_severity == "error":
                    self.errors.append(
                        DataValidationError(resource_type, resource_id, field, message)
                    )
                else:
                    self.warnings.append(
                        DataValidationWarning(resource_type, resource_id, f"{field}: {message}")
                    )
        except Exception as e:
            # Catch any other exceptions
            self.failed_uris += 1
            message = f"URI check failed: {uri} ({str(e)})"
            if self.uri_check_severity == "error":
                self.errors.append(
                    DataValidationError(resource_type, resource_id, field, message)
                )
            else:
                self.warnings.append(
                    DataValidationWarning(resource_type, resource_id, f"{field}: {message}")
                )

    def extract_uris_from_data(self, data: dict[str, Any]) -> list[tuple[str, str]]:
        """Extract URIs from item or media data
        
        Returns list of (field_name, uri) tuples
        """
        uris = []

        # Check @id fields in properties
        for key, value in data.items():
            if not key.startswith("dcterms:"):
                continue

            if isinstance(value, list):
                for idx, prop in enumerate(value):
                    if isinstance(prop, dict):
                        uri = prop.get("@id")
                        if uri and isinstance(uri, str):
                            uris.append((f"{key}[{idx}].@id", uri))

        # Check o:original_url for media
        if "o:original_url" in data and data["o:original_url"]:
            uris.append(("o:original_url", data["o:original_url"]))

        return uris

    def _validate_vocabularies(self, data: dict[str, Any], resource_type: str, resource_id: int) -> None:
        """Validate vocabulary-controlled fields"""
        # Validate dcterms:temporal (Era)
        temporal_values = data.get("dcterms:temporal", [])
        if isinstance(temporal_values, list):
            for idx, item in enumerate(temporal_values):
                if isinstance(item, dict):
                    value = item.get("@value")
                    if value and not self.vocab_loader.is_valid_era(value):
                        self.errors.append(
                            DataValidationError(
                                resource_type,
                                resource_id,
                                f"dcterms:temporal[{idx}]",
                                f"Value must be from Era vocabulary: {value}"
                            )
                        )
        
        # Validate dcterms:format (MIME type)
        format_values = data.get("dcterms:format", [])
        if isinstance(format_values, list):
            for idx, item in enumerate(format_values):
                if isinstance(item, dict):
                    value = item.get("@value")
                    if value and not self.vocab_loader.is_valid_mime_type(value):
                        self.errors.append(
                            DataValidationError(
                                resource_type,
                                resource_id,
                                f"dcterms:format[{idx}]",
                                f"Value must be from MIME type vocabulary: {value}"
                            )
                        )
        
        # Validate dcterms:license
        license_values = data.get("dcterms:license", [])
        if isinstance(license_values, list):
            for idx, item in enumerate(license_values):
                if isinstance(item, dict):
                    value = item.get("@value")
                    if value and not self.vocab_loader.is_valid_license(value):
                        self.errors.append(
                            DataValidationError(
                                resource_type,
                                resource_id,
                                f"dcterms:license[{idx}]",
                                f"Invalid license URI: {value}"
                            )
                        )
        
        # Validate dcterms:type
        type_values = data.get("dcterms:type", [])
        if isinstance(type_values, list):
            for idx, item in enumerate(type_values):
                if isinstance(item, dict):
                    value = item.get("@id")
                    if value and not self.vocab_loader.is_valid_type(value):
                        self.errors.append(
                            DataValidationError(
                                resource_type,
                                resource_id,
                                f"dcterms:type[{idx}]",
                                f"Invalid type URI (must be Image or Dataset): {value}"
                            )
                        )
        
        # Validate dcterms:language
        language_values = data.get("dcterms:language", [])
        if isinstance(language_values, list):
            for idx, item in enumerate(language_values):
                if isinstance(item, dict):
                    value = item.get("@value")
                    if value and not self.vocab_loader.is_valid_language(value):
                        self.errors.append(
                            DataValidationError(
                                resource_type,
                                resource_id,
                                f"dcterms:language[{idx}]",
                                f"Invalid language code (must be de, fr, sp, or lat): {value}"
                            )
                        )
        
        # Validate dcterms:subject (Iconclass)
        subject_values = data.get("dcterms:subject", [])
        if isinstance(subject_values, list):
            for idx, item in enumerate(subject_values):
                if isinstance(item, dict):
                    value = item.get("@value")
                    # Only validate if it looks like an Iconclass code (starts with numbers)
                    if value and value[0].isdigit() and not self.vocab_loader.is_valid_iconclass(value):
                        self.errors.append(
                            DataValidationError(
                                resource_type,
                                resource_id,
                                f"dcterms:subject[{idx}]",
                                f"Invalid Iconclass code: {value}"
                            )
                        )

    async def check_uris_for_resource(
        self, data: dict[str, Any], resource_type: str, resource_id: int
    ) -> None:
        """Check all URIs in a resource"""
        if not self.check_uris:
            return

        uris = self.extract_uris_from_data(data)
        if uris:
            tasks = [
                self.check_uri_async(uri, resource_type, resource_id, field)
                for field, uri in uris
            ]
            await asyncio.gather(*tasks)

    def validate_item(self, item_data: dict[str, Any]) -> None:
        """Validate a single item"""
        try:
            Item.model_validate(item_data)
            self.validated_items += 1
            
            # Additional vocabulary validations
            item_id = item_data.get("o:id", "unknown")
            self._validate_vocabularies(item_data, "Item", item_id)

            # Check URIs if enabled
            if self.check_uris:
                asyncio.run(self.check_uris_for_resource(item_data, "Item", item_id))

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
            
            # Additional vocabulary validations
            media_id = media_data.get("o:id", "unknown")
            self._validate_vocabularies(media_data, "Media", media_id)

            # Check URIs if enabled
            if self.check_uris:
                asyncio.run(self.check_uris_for_resource(media_data, "Media", media_id))

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
            print(f"\rValidating item {idx}/{len(items)}...        ", end="", flush=True)
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
                    print(f"\n\rWarning: Could not fetch media for item {item_id}: {e}")

        print("\r" + " " * 80 + "\r", end="")  # Clear progress line
        
        # Show URI checking summary if enabled
        if self.check_uris and self.checked_uris > 0:
            print(f"Checked {self.checked_uris} URIs, {self.failed_uris} failed")
        else:
            print()  # Just add a newline

    def print_report(self) -> None:
        """Print validation report"""
        print("\n" + "=" * 80)
        print("VALIDATION REPORT")
        print("=" * 80)
        print(f"Items validated: {self.validated_items}")
        print(f"Media validated: {self.validated_media}")
        print(f"Total errors: {len(self.errors)}")
        print(f"Total warnings: {len(self.warnings)}")
        if self.check_uris:
            print(f"URIs checked: {self.checked_uris}")
            print(f"Failed URIs: {self.failed_uris}")
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
            if self.check_uris:
                f.write(f"URIs checked: {self.checked_uris}\n")
                f.write(f"Failed URIs: {self.failed_uris}\n")
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
        "--check-redirects",
        action="store_true",
        help="Check for redirects and warn if URLs redirect to different domains (requires --check-uris)",
    )
    parser.add_argument(
        "--uri-check-severity",
        choices=["warning", "error"],
        default="warning",
        help="Severity level for failed URI checks: warning (default) or error",
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
    if args.check_uris:
        print(f"URI checking: enabled (severity: {args.uri_check_severity})")
        if args.check_redirects:
            print("Redirect checking: enabled")
    print()

    validator = OmekaValidator(
        args.base_url,
        args.api_key,
        args.check_uris,
        args.check_redirects,
        args.uri_check_severity,
    )

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
