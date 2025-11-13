"""
Omeka S data validator for Stadt.Geschichte.Basel project.

This module validates items and media from the Omeka S API against
a comprehensive data model using pydantic.
"""

import argparse
import asyncio
import os
import random
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from src.models import Item, Media
from src.vocabularies import VocabularyLoader

# List of realistic User-Agent strings to rotate through
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


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
        key_identity: str | None = None,
        key_credential: str | None = None,
        check_uris: bool = False,
        check_redirects: bool = False,
        uri_check_severity: str = "warning",
        enable_profiling: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.key_identity = key_identity
        self.key_credential = key_credential
        self.check_uris = check_uris
        self.check_redirects = check_redirects
        self.uri_check_severity = uri_check_severity
        self.enable_profiling = enable_profiling
        self.errors: list[DataValidationError] = []
        self.warnings: list[DataValidationWarning] = []
        self.validated_items = 0
        self.validated_media = 0
        self.checked_uris = 0
        self.failed_uris = 0
        # Bounded LRU cache for URI checks (max 10000 entries)
        self.uri_cache: OrderedDict[str, tuple[int, str | None]] = OrderedDict()
        self.uri_cache_max_size = 10000

        # Store raw data for profiling
        self.items_data: list[dict[str, Any]] = []
        self.media_data: list[dict[str, Any]] = []

        # Track identifiers for uniqueness validation
        self.item_identifiers: dict[str, list[int]] = {}  # identifier -> [item_ids]
        self.media_identifiers: dict[str, list[int]] = {}  # identifier -> [media_ids]

        self.client = httpx.Client(timeout=30.0)

        vocab_file = Path(__file__).parent / "data" / "raw" / "vocabularies.json"
        self.vocab_loader = VocabularyLoader(vocab_file)

    def _add_auth_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add authentication parameters if configured."""
        if self.key_identity and self.key_credential:
            params["key_identity"] = self.key_identity
            params["key_credential"] = self.key_credential
        return params

    def fetch_items(self, item_set_id: int) -> list[dict[str, Any]]:
        """Fetch all items from an item set"""
        items: list[dict[str, Any]] = []
        page = 1
        per_page = 50

        while True:
            url = f"{self.base_url}/api/items"
            params = self._add_auth_params(
                {"item_set_id": item_set_id, "page": page, "per_page": per_page}
            )

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
        params = self._add_auth_params({"item_id": item_id})
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def check_single_uri(self, uri: str) -> tuple[int, str | None]:
        """Check a single URI and return (status_code, redirect_location)"""
        # Check cache first (LRU: move to end if found)
        if uri in self.uri_cache:
            self.uri_cache.move_to_end(uri)
            return self.uri_cache[uri]

        # Rotate through user agents to avoid being blocked
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        async with httpx.AsyncClient(
            timeout=10.0, follow_redirects=False, headers=headers
        ) as client:
            try:
                # Try HEAD request first
                response = await client.head(uri)
                status_code = response.status_code
                redirect_location = response.headers.get("location")

                # If server doesn't support HEAD (405 or 501), try GET
                if status_code in (405, 501):
                    try:
                        response = await client.get(uri, timeout=10.0)
                        status_code = response.status_code
                        redirect_location = response.headers.get("location")
                    except (httpx.RequestError, httpx.HTTPError) as ge:
                        result = (-1, str(ge))
                        self._cache_uri_result(uri, result)
                        return result

                # Cache and return the result
                result = (status_code, redirect_location)
                self._cache_uri_result(uri, result)
                return result

            except (httpx.RequestError, httpx.HTTPError) as e:
                # Return a special status code for network exceptions
                result = (-1, str(e))
                self._cache_uri_result(uri, result)
                return result

    def _cache_uri_result(self, uri: str, result: tuple[int, str | None]) -> None:
        """Add result to bounded LRU cache, evicting oldest if at max size."""
        if uri in self.uri_cache:
            # Update existing entry and move to end
            self.uri_cache[uri] = result
            self.uri_cache.move_to_end(uri)
        else:
            # Add new entry
            self.uri_cache[uri] = result
            # Evict oldest entry if cache is full
            if len(self.uri_cache) > self.uri_cache_max_size:
                self.uri_cache.popitem(last=False)  # Remove oldest (FIFO)

    async def check_uri_async(
        self, uri: str, resource_type: str, resource_id: int, field: str
    ) -> None:
        """Check if a URI is reachable asynchronously"""
        if not uri or not uri.startswith(("http://", "https://")):
            return

        self.checked_uris += 1
        # Truncate long URIs for display
        display_uri = uri if len(uri) <= 60 else uri[:57] + "..."
        print(
            f"\rChecking URI ({self.checked_uris}): {display_uri}        ",
            end="",
            flush=True,
        )

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
                    DataValidationWarning(
                        resource_type, resource_id, f"{field}: {message}"
                    )
                )
            return

        # Check for redirects
        if self.check_redirects and status_code in (301, 302, 303, 307, 308):
            # Check if redirect is to a different domain
            if redirect_location:
                # Parse original URI
                parsed_original = urlparse(uri)
                # Resolve redirect location (could be relative)
                absolute_redirect = urljoin(uri, redirect_location)
                parsed_redirect = urlparse(absolute_redirect)

                # Normalize netlocs (lowercase, remove default ports)
                original_netloc = parsed_original.netloc.lower()
                redirect_netloc = parsed_redirect.netloc.lower()

                # Compare netlocs
                if original_netloc != redirect_netloc:
                    message = (
                        f"URI redirects to different domain: "
                        f"{uri} -> {absolute_redirect}"
                    )
                    self.warnings.append(
                        DataValidationWarning(
                            resource_type, resource_id, f"{field}: {message}"
                        )
                    )

        # Check for HTTP errors
        if status_code >= 400:
            self.failed_uris += 1
            message = f"URI returned HTTP {status_code}: {uri}"
            # 404 errors are always treated as errors
            if status_code == 404 or self.uri_check_severity == "error":
                self.errors.append(
                    DataValidationError(resource_type, resource_id, field, message)
                )
            else:
                self.warnings.append(
                    DataValidationWarning(
                        resource_type, resource_id, f"{field}: {message}"
                    )
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

    def _validate_vocabularies(
        self, data: dict[str, Any], resource_type: str, resource_id: int
    ) -> None:
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
                                f"Value must be from Era vocabulary: {value}",
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
                                f"Value must be from MIME type vocabulary: {value}",
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
                                f"Invalid license URI: {value}",
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
                                f"Invalid type URI (must be Image or Dataset): {value}",
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
                                f"Invalid language code (must be valid ISO 639-1 "
                                f"two-letter code): {value}",
                            )
                        )

        # Validate dcterms:subject (Iconclass)
        subject_values = data.get("dcterms:subject", [])
        if isinstance(subject_values, list):
            for idx, item in enumerate(subject_values):
                if isinstance(item, dict):
                    value = item.get("@value")
                    # Only validate if it looks like an Iconclass code (starts with numbers)
                    if (
                        value
                        and value[0].isdigit()
                        and not self.vocab_loader.is_valid_iconclass(value)
                    ):
                        self.errors.append(
                            DataValidationError(
                                resource_type,
                                resource_id,
                                f"dcterms:subject[{idx}]",
                                f"Invalid Iconclass code: {value}",
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

    def _check_missing_field(self, data: dict[str, Any], field_name: str) -> bool:
        """Check if a field is missing or empty"""
        value = data.get(field_name)
        if value is None:
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False

    def _extract_identifier_value(self, data: dict[str, Any]) -> str | None:
        """Extract the identifier value from dcterms:identifier field"""
        identifiers = data.get("dcterms:identifier")
        if identifiers and isinstance(identifiers, list) and len(identifiers) > 0:
            first_identifier = identifiers[0]
            if isinstance(first_identifier, dict):
                return first_identifier.get("@value")
        return None

    def _check_thumbnail_or_media(self, data: dict[str, Any]) -> bool:
        """Check if any thumbnails or media are missing"""
        # Check thumbnail_display_urls
        thumbnails = data.get("thumbnail_display_urls")
        has_thumbnails = False
        if thumbnails and isinstance(thumbnails, dict):
            has_thumbnails = bool(
                thumbnails.get("large")
                or thumbnails.get("medium")
                or thumbnails.get("small")
            )

        # Check o:media for items
        media = data.get("o:media")
        has_media = media and isinstance(media, list) and len(media) > 0

        # Return True if BOTH are missing
        return not has_thumbnails and not has_media

    def _contains_url(self, text: str) -> bool:
        """Check if text contains a URL pattern

        Detects URLs starting with http://, https://, ftp://, or www.
        """
        if not text or not isinstance(text, str):
            return False

        # Pattern to match common URL formats
        url_pattern = r"(?:https?://|ftp://|www\.)[^\s]+"
        return bool(re.search(url_pattern, text, re.IGNORECASE))

    def _check_literal_fields_for_urls(
        self, data: dict[str, Any], resource_type: str, resource_id: int
    ) -> None:
        """Check if literal type fields contain URLs (issue #22)"""
        # Check all dcterms fields
        for key, value in data.items():
            if not key.startswith("dcterms:"):
                continue

            if isinstance(value, list):
                for idx, prop in enumerate(value):
                    if isinstance(prop, dict):
                        # Check if this is a literal type field
                        field_type = prop.get("type")
                        if field_type == "literal":
                            field_value = prop.get("@value")
                            if field_value and self._contains_url(field_value):
                                display_value = field_value[:80]
                                if len(field_value) > 80:
                                    display_value += "..."
                                self.warnings.append(
                                    DataValidationWarning(
                                        resource_type,
                                        resource_id,
                                        f"{key}[{idx}]: Literal field contains "
                                        f"URL: {display_value}",
                                    )
                                )

    def _validate_item_additional_checks(
        self, item_data: dict[str, Any], item_id: int
    ) -> None:
        """Additional validation checks for items per issue #16"""
        # Errors (missing required fields)
        if not item_data.get("o:title"):
            self.errors.append(
                DataValidationError("Item", item_id, "o:title", "Field is required")
            )

        if self._check_missing_field(item_data, "dcterms:identifier"):
            self.errors.append(
                DataValidationError(
                    "Item", item_id, "dcterms:identifier", "Field is required"
                )
            )

        if self._check_missing_field(item_data, "dcterms:description"):
            self.errors.append(
                DataValidationError(
                    "Item", item_id, "dcterms:description", "Field is required"
                )
            )

        if self._check_missing_field(item_data, "dcterms:temporal"):
            self.errors.append(
                DataValidationError(
                    "Item", item_id, "dcterms:temporal", "Field is required"
                )
            )

        # Warnings (missing recommended fields)
        if self._check_thumbnail_or_media(item_data):
            self.warnings.append(
                DataValidationWarning(
                    "Item",
                    item_id,
                    "Missing thumbnails (large, medium, small) or media",
                )
            )

        if self._check_missing_field(item_data, "dcterms:language"):
            self.warnings.append(
                DataValidationWarning("Item", item_id, "Missing dcterms:language")
            )

        if self._check_missing_field(item_data, "dcterms:isPartOf"):
            self.warnings.append(
                DataValidationWarning("Item", item_id, "Missing dcterms:isPartOf")
            )

    def _validate_media_additional_checks(
        self, media_data: dict[str, Any], media_id: int
    ) -> None:
        """Additional validation checks for media per issue #16"""
        # Errors (missing required fields)
        if not media_data.get("o:title"):
            self.errors.append(
                DataValidationError("Media", media_id, "o:title", "Field is required")
            )

        if self._check_missing_field(media_data, "dcterms:identifier"):
            self.errors.append(
                DataValidationError(
                    "Media", media_id, "dcterms:identifier", "Field is required"
                )
            )

        if self._check_missing_field(media_data, "dcterms:description"):
            self.errors.append(
                DataValidationError(
                    "Media", media_id, "dcterms:description", "Field is required"
                )
            )

        if self._check_missing_field(media_data, "dcterms:rights"):
            self.errors.append(
                DataValidationError(
                    "Media", media_id, "dcterms:rights", "Field is required"
                )
            )

        if self._check_missing_field(media_data, "dcterms:license"):
            self.errors.append(
                DataValidationError(
                    "Media", media_id, "dcterms:license", "Field is required"
                )
            )

        # Warnings (missing recommended fields)
        # Check if both o:resource_template.@id and o:resource_template.o:id are missing
        resource_template = media_data.get("o:resource_template")
        if not resource_template or (
            not resource_template.get("@id") and not resource_template.get("o:id")
        ):
            self.warnings.append(
                DataValidationWarning(
                    "Media", media_id, "Missing o:resource_template (@id and o:id)"
                )
            )

        if self._check_thumbnail_or_media(media_data):
            self.warnings.append(
                DataValidationWarning(
                    "Media",
                    media_id,
                    "Missing thumbnails (large, medium, small) or media",
                )
            )

        if self._check_missing_field(media_data, "dcterms:creator"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:creator")
            )

        if self._check_missing_field(media_data, "dcterms:publisher"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:publisher")
            )

        if self._check_missing_field(media_data, "dcterms:temporal"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:temporal")
            )

        if self._check_missing_field(media_data, "dcterms:type"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:type")
            )

        if self._check_missing_field(media_data, "dcterms:format"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:format")
            )

        if self._check_missing_field(media_data, "dcterms:extent"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:extent")
            )

        if self._check_missing_field(media_data, "dcterms:source"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:source")
            )

        if self._check_missing_field(media_data, "dcterms:language"):
            self.warnings.append(
                DataValidationWarning("Media", media_id, "Missing dcterms:language")
            )

    def _check_duplicate_identifiers(self) -> None:
        """Check for duplicate identifiers and generate errors for all entries with duplicates"""
        # Check for duplicate item identifiers
        for identifier, item_ids in self.item_identifiers.items():
            if len(item_ids) > 1:
                for item_id in item_ids:
                    self.errors.append(
                        DataValidationError(
                            "Item",
                            item_id,
                            "dcterms:identifier",
                            f"Duplicate identifier '{identifier}' found in items: {item_ids}",
                        )
                    )

        # Check for duplicate media identifiers
        for identifier, media_ids in self.media_identifiers.items():
            if len(media_ids) > 1:
                for media_id in media_ids:
                    self.errors.append(
                        DataValidationError(
                            "Media",
                            media_id,
                            "dcterms:identifier",
                            f"Duplicate identifier '{identifier}' found in media: {media_ids}",
                        )
                    )

    def validate_item(self, item_data: dict[str, Any]) -> None:
        """Validate a single item"""
        # Store raw data for profiling if enabled
        if self.enable_profiling:
            self.items_data.append(item_data)

        item_id = item_data.get("o:id", "unknown")

        # Track identifier for uniqueness checking
        identifier_value = self._extract_identifier_value(item_data)
        if identifier_value:
            if identifier_value not in self.item_identifiers:
                self.item_identifiers[identifier_value] = []
            self.item_identifiers[identifier_value].append(item_id)

        try:
            Item.model_validate(item_data)
            self.validated_items += 1

            # Additional vocabulary validations
            self._validate_vocabularies(item_data, "Item", item_id)

            # Additional field presence checks (issue #16)
            self._validate_item_additional_checks(item_data, item_id)

            # Check for URLs in literal fields (issue #22)
            self._check_literal_fields_for_urls(item_data, "Item", item_id)

            # Check URIs if enabled
            if self.check_uris:
                asyncio.run(self.check_uris_for_resource(item_data, "Item", item_id))

        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                self.errors.append(
                    DataValidationError("Item", item_id, field, error["msg"])
                )

    def validate_media(self, media_data: dict[str, Any]) -> None:
        """Validate a single media object"""
        # Store raw data for profiling if enabled
        if self.enable_profiling:
            self.media_data.append(media_data)

        media_id = media_data.get("o:id", "unknown")

        # Track identifier for uniqueness checking
        identifier_value = self._extract_identifier_value(media_data)
        if identifier_value:
            if identifier_value not in self.media_identifiers:
                self.media_identifiers[identifier_value] = []
            self.media_identifiers[identifier_value].append(media_id)

        try:
            Media.model_validate(media_data)
            self.validated_media += 1

            # Additional vocabulary validations
            self._validate_vocabularies(media_data, "Media", media_id)

            # Additional field presence checks (issue #16)
            self._validate_media_additional_checks(media_data, media_id)

            # Check for URLs in literal fields (issue #22)
            self._check_literal_fields_for_urls(media_data, "Media", media_id)

            # Check URIs if enabled
            if self.check_uris:
                asyncio.run(self.check_uris_for_resource(media_data, "Media", media_id))

        except ValidationError as e:
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
            print(
                f"\rValidating item {idx}/{len(items)}...        ", end="", flush=True
            )
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

        # Check for duplicate identifiers
        self._check_duplicate_identifiers()

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
        # Ensure parent directory exists when a path with directories is provided
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
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

        print(f"\nReport saved to: {output_path}")

    def export_validation_csv(
        self, output_dir: str | Path = "validation_reports"
    ) -> None:
        """Export validation results as CSV files per issue #17.

        Creates three CSV files:
        - items_validation.csv: validation results for items
        - media_validation.csv: validation results for media
        - validation_summary.csv: summary of validation results

        Each row represents one item/media, each column a validation field.
        Empty cells mean valid, non-empty cells contain error/warning messages.
        Each CSV includes an edit_link column for direct access to Omeka admin.
        """
        import csv
        from collections import defaultdict

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build admin base URL from API URL
        # Replace /api with /admin, or add /admin if no /api present
        if "/api" in self.base_url:
            admin_base_url = self.base_url.replace("/api", "/admin")
        else:
            admin_base_url = f"{self.base_url.rstrip('/')}/admin"

        # Organize errors and warnings by resource
        item_issues: dict[int, dict[str, str]] = defaultdict(dict)
        media_issues: dict[int, dict[str, str]] = defaultdict(dict)

        # Process errors
        for error in self.errors:
            issue_dict = item_issues if error.resource_type == "Item" else media_issues
            # Format: "error: <message>"
            issue_dict[error.resource_id][error.field] = f"error: {error.error}"

        # Process warnings
        for warning in self.warnings:
            issue_dict = (
                item_issues if warning.resource_type == "Item" else media_issues
            )
            # Extract field name from warning message if possible
            # Format: "warning: <message>"
            # If message contains field name, use it as key, otherwise use "general"
            field_name = "general"
            message = warning.message
            if ":" in message and not message.startswith("Missing"):
                # Extract field from format "field: message"
                parts = message.split(":", 1)
                field_name = parts[0].strip()
                message = parts[1].strip()
            elif message.startswith("Missing "):
                # Extract field from "Missing <field>"
                field_name = message.replace("Missing ", "").strip()
                message = "Missing field"

            issue_dict[warning.resource_id][field_name] = f"warning: {message}"

        # Get all unique field names for items and media
        item_fields = set()
        for issues in item_issues.values():
            item_fields.update(issues.keys())
        item_fields = sorted(item_fields)

        media_fields = set()
        for issues in media_issues.values():
            media_fields.update(issues.keys())
        media_fields = sorted(media_fields)

        # Export items validation CSV
        if item_issues:
            items_csv = output_dir / "items_validation.csv"
            with open(items_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header: resource_id, edit_link, then all field names
                writer.writerow(["resource_id", "edit_link"] + item_fields)

                # Write rows sorted by resource_id
                for resource_id in sorted(item_issues.keys()):
                    issues = item_issues[resource_id]
                    edit_link = f"{admin_base_url}/items/{resource_id}"
                    row = [resource_id, edit_link]
                    # Add field values (empty if no issue)
                    row.extend(issues.get(field, "") for field in item_fields)
                    writer.writerow(row)

            print(f"Items validation CSV saved to: {items_csv}")

        # Export media validation CSV
        if media_issues:
            media_csv = output_dir / "media_validation.csv"
            with open(media_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header: resource_id, edit_link, then all field names
                writer.writerow(["resource_id", "edit_link"] + media_fields)

                # Write rows sorted by resource_id
                for resource_id in sorted(media_issues.keys()):
                    issues = media_issues[resource_id]
                    edit_link = f"{admin_base_url}/media/{resource_id}"
                    row = [resource_id, edit_link]
                    # Add field values (empty if no issue)
                    row.extend(issues.get(field, "") for field in media_fields)
                    writer.writerow(row)

            print(f"Media validation CSV saved to: {media_csv}")

        # Export summary CSV
        summary_csv = output_dir / "validation_summary.csv"
        with open(summary_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            writer.writerow(["items_validated", self.validated_items])
            writer.writerow(["media_validated", self.validated_media])
            writer.writerow(["total_errors", len(self.errors)])
            writer.writerow(["total_warnings", len(self.warnings)])
            writer.writerow(["items_with_issues", len(item_issues)])
            writer.writerow(["media_with_issues", len(media_issues)])
            if self.check_uris:
                writer.writerow(["uris_checked", self.checked_uris])
                writer.writerow(["failed_uris", self.failed_uris])

        print(f"Validation summary CSV saved to: {summary_csv}")
        print(f"\nAll CSV reports saved to: {output_dir}/")

    def generate_profiling_reports(
        self, output_dir: str | Path = "analysis", minimal: bool = False
    ) -> None:
        """Generate data profiling reports using ydata-profiling.

        Args:
            output_dir: Directory to save profiling outputs
            minimal: If True, generate minimal reports for faster processing
        """
        if not self.enable_profiling:
            print("Profiling is not enabled. Use --profile to enable data profiling.")
            return

        if not self.items_data and not self.media_data:
            print("No data collected for profiling.")
            return

        # Lazy import profiling modules
        try:
            from src.profiling import analyze_items, analyze_media
        except ImportError as e:
            print(
                "\nError: Profiling dependencies are not installed.",
                file=sys.stderr,
            )
            print(
                "Please install the profiling dependencies with: uv sync",
                file=sys.stderr,
            )
            print(
                "Or install ydata-profiling manually: pip install ydata-profiling",
                file=sys.stderr,
            )
            print(f"\nDetails: {e}", file=sys.stderr)
            return

        output_dir = Path(output_dir)
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nGenerating profiling reports in {output_dir}/...")

        if self.items_data:
            print(f"  Profiling {len(self.items_data)} items...")
            analyze_items(self.items_data, output_dir, minimal=minimal)
            print(f"    - Items DataFrame saved to {output_dir}/items.csv")
            print(
                f"    - Items profile report saved to {output_dir}/items_profile.html"
            )

        if self.media_data:
            print(f"  Profiling {len(self.media_data)} media...")
            analyze_media(self.media_data, output_dir, minimal=minimal)
            print(f"    - Media DataFrame saved to {output_dir}/media.csv")
            print(
                f"    - Media profile report saved to {output_dir}/media_profile.html"
            )

        print("\nProfiling complete!")


def main() -> int:
    """Main entry point"""
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Get defaults from environment variables
    env_base_url = os.getenv("OMEKA_URL", "https://omeka.unibe.ch")
    env_item_set_id = int(os.getenv("ITEM_SET_ID", "10780"))
    env_key_identity = os.getenv("KEY_IDENTITY")
    env_key_credential = os.getenv("KEY_CREDENTIAL")

    parser = argparse.ArgumentParser(
        description="Validate Omeka S data against Stadt.Geschichte.Basel data model"
    )
    parser.add_argument(
        "--base-url",
        default=env_base_url,
        help=f"Base URL of the Omeka S instance (default: {env_base_url})",
    )
    parser.add_argument(
        "--item-set-id",
        type=int,
        default=env_item_set_id,
        help=f"Item set ID to validate (default: {env_item_set_id})",
    )
    parser.add_argument(
        "--key-identity",
        default=env_key_identity,
        help="Optional API key identity for authentication (can be set in .env as KEY_IDENTITY)",
    )
    parser.add_argument(
        "--key-credential",
        default=env_key_credential,
        help="Optional API key credential for authentication (can be set in .env as KEY_CREDENTIAL)",
    )
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
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable data profiling and generate analysis reports",
    )
    parser.add_argument(
        "--profile-minimal",
        action="store_true",
        help="Generate minimal profiling reports (faster, less detailed)",
    )
    parser.add_argument(
        "--profile-output",
        type=Path,
        default="analysis",
        help="Directory for profiling outputs (default: analysis/)",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export validation results as CSV files (items, media, and summary)",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default="validation_reports",
        help="Directory for CSV validation reports (default: validation_reports/)",
    )

    args = parser.parse_args()

    print("Stadt.Geschichte.Basel Data Validator")
    print(f"Base URL: {args.base_url}")
    print(f"Item Set ID: {args.item_set_id}")
    if args.check_uris:
        print(f"URI checking: enabled (severity: {args.uri_check_severity})")
        if args.check_redirects:
            print("Redirect checking: enabled")
    if args.profile:
        print(f"Data profiling: enabled (output: {args.profile_output}/)")
    if args.export_csv:
        print(f"CSV export: enabled (output: {args.csv_output}/)")
    print()

    validator = OmekaValidator(
        args.base_url,
        args.key_identity,
        args.key_credential,
        args.check_uris,
        args.check_redirects,
        args.uri_check_severity,
        args.profile,
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

    if args.export_csv:
        validator.export_validation_csv(args.csv_output)

    if args.profile:
        validator.generate_profiling_reports(args.profile_output, args.profile_minimal)

    return 0 if not validator.errors else 1


if __name__ == "__main__":
    sys.exit(main())
