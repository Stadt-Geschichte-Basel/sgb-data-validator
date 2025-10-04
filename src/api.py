"""
API for interacting with Omeka S item sets, items, and media.

This module provides a high-level API for:
- Reading and saving item sets, items, and media
- Validating data against the data model
- Backing up and restoring data
- Updating resources
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from src.models import Item, Media
from src.vocabularies import VocabularyLoader


class OmekaAPI:
    """High-level API for interacting with Omeka S resources"""

    def __init__(
        self, base_url: str, api_key: str | None = None, timeout: float = 30.0
    ) -> None:
        """
        Initialize the Omeka API client.

        Args:
            base_url: Base URL of the Omeka S instance
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        headers = {}
        if api_key:
            headers["key_identity"] = api_key

        self.client = httpx.Client(headers=headers, timeout=timeout)

        # Initialize vocabulary loader for validation
        vocab_file = Path(__file__).parent.parent / "data" / "raw" / "vocabularies.json"
        self.vocab_loader = VocabularyLoader(vocab_file)

    def __enter__(self) -> "OmekaAPI":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()

    def close(self) -> None:
        """Close the HTTP client"""
        self.client.close()

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    def get_item_set(self, item_set_id: int) -> dict[str, Any]:
        """
        Get a single item set by ID.

        Args:
            item_set_id: The ID of the item set

        Returns:
            The item set data as a dictionary

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        url = f"{self.base_url}/api/item_sets/{item_set_id}"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def get_item_sets(
        self, page: int = 1, per_page: int = 50, **filters: Any
    ) -> list[dict[str, Any]]:
        """
        Get a list of item sets with optional filters.

        Args:
            page: Page number for pagination
            per_page: Number of items per page
            **filters: Additional filter parameters

        Returns:
            List of item set data dictionaries
        """
        url = f"{self.base_url}/api/item_sets"
        params = {"page": page, "per_page": per_page, **filters}
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_items_from_set(
        self, item_set_id: int, page: int | None = None, per_page: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get all items from an item set.

        Args:
            item_set_id: The ID of the item set
            page: Optional page number (if None, fetches all pages)
            per_page: Number of items per page

        Returns:
            List of item data dictionaries
        """
        if page is not None:
            # Fetch single page
            url = f"{self.base_url}/api/items"
            params = {"item_set_id": item_set_id, "page": page, "per_page": per_page}
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        # Fetch all pages
        items: list[dict[str, Any]] = []
        current_page = 1
        while True:
            url = f"{self.base_url}/api/items"
            params = {
                "item_set_id": item_set_id,
                "page": current_page,
                "per_page": per_page,
            }
            response = self.client.get(url, params=params)
            response.raise_for_status()
            page_items = response.json()
            if not page_items:
                break
            items.extend(page_items)
            current_page += 1
        return items

    def get_item(self, item_id: int) -> dict[str, Any]:
        """
        Get a single item by ID.

        Args:
            item_id: The ID of the item

        Returns:
            The item data as a dictionary
        """
        url = f"{self.base_url}/api/items/{item_id}"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def get_media(self, media_id: int) -> dict[str, Any]:
        """
        Get a single media resource by ID.

        Args:
            media_id: The ID of the media

        Returns:
            The media data as a dictionary
        """
        url = f"{self.base_url}/api/media/{media_id}"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def get_media_from_item(self, item_id: int) -> list[dict[str, Any]]:
        """
        Get all media for an item.

        Args:
            item_id: The ID of the item

        Returns:
            List of media data dictionaries
        """
        url = f"{self.base_url}/api/media"
        params = {"item_id": item_id}
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # SAVE OPERATIONS
    # =========================================================================

    def save_to_file(
        self, data: dict[str, Any] | list[dict[str, Any]], filepath: Path | str
    ) -> None:
        """
        Save data to a JSON file.

        Args:
            data: Data to save (dict or list of dicts)
            filepath: Path where to save the file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(
        self, filepath: Path | str
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Load data from a JSON file.

        Args:
            filepath: Path to the file to load

        Returns:
            The loaded data
        """
        filepath = Path(filepath)
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

    # =========================================================================
    # VALIDATION OPERATIONS
    # =========================================================================

    def validate_item(self, item_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate an item against the data model.

        Args:
            item_data: The item data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        try:
            Item.model_validate(item_data)
            return True, []
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            return False, errors

    def validate_media(self, media_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate a media resource against the data model.

        Args:
            media_data: The media data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        try:
            Media.model_validate(media_data)
            return True, []
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            return False, errors

    def validate_item_set(self, item_set_id: int) -> dict[str, Any]:
        """
        Validate all items and media in an item set.

        Args:
            item_set_id: The ID of the item set to validate

        Returns:
            Dictionary containing validation results with counts and errors
        """
        results = {
            "item_set_id": item_set_id,
            "timestamp": datetime.now().isoformat(),
            "items_validated": 0,
            "items_valid": 0,
            "items_invalid": 0,
            "media_validated": 0,
            "media_valid": 0,
            "media_invalid": 0,
            "errors": [],
        }

        # Get all items in the set
        items = self.get_items_from_set(item_set_id)

        for item_data in items:
            item_id = item_data.get("o:id", "unknown")
            results["items_validated"] += 1

            # Validate item
            is_valid, errors = self.validate_item(item_data)
            if is_valid:
                results["items_valid"] += 1
            else:
                results["items_invalid"] += 1
                for error in errors:
                    results["errors"].append(
                        {"type": "item", "id": item_id, "error": error}
                    )

            # Get and validate media
            try:
                media_list = self.get_media_from_item(item_id)
                for media_data in media_list:
                    media_id = media_data.get("o:id", "unknown")
                    results["media_validated"] += 1

                    is_valid, errors = self.validate_media(media_data)
                    if is_valid:
                        results["media_valid"] += 1
                    else:
                        results["media_invalid"] += 1
                        for error in errors:
                            results["errors"].append(
                                {"type": "media", "id": media_id, "error": error}
                            )
            except httpx.HTTPStatusError:
                # Media fetch failed, skip
                pass

        return results

    # =========================================================================
    # BACKUP AND RESTORE OPERATIONS
    # =========================================================================

    def backup_item_set(
        self, item_set_id: int, backup_dir: Path | str
    ) -> dict[str, Path]:
        """
        Backup an item set, including all items and media.

        Args:
            item_set_id: The ID of the item set to backup
            backup_dir: Directory where to save the backup

        Returns:
            Dictionary mapping resource types to file paths
        """
        backup_dir = Path(backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"itemset_{item_set_id}_{timestamp}"
        backup_path = backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        # Backup item set metadata
        item_set_data = self.get_item_set(item_set_id)
        item_set_file = backup_path / "item_set.json"
        self.save_to_file(item_set_data, item_set_file)

        # Backup all items
        items = self.get_items_from_set(item_set_id)
        items_file = backup_path / "items.json"
        self.save_to_file(items, items_file)

        # Backup all media
        all_media = []
        for item in items:
            item_id = item.get("o:id")
            if item_id:
                try:
                    media_list = self.get_media_from_item(item_id)
                    all_media.extend(media_list)
                except httpx.HTTPStatusError:
                    pass

        media_file = backup_path / "media.json"
        self.save_to_file(all_media, media_file)

        # Create backup manifest
        manifest = {
            "item_set_id": item_set_id,
            "timestamp": timestamp,
            "items_count": len(items),
            "media_count": len(all_media),
            "files": {
                "item_set": str(item_set_file.relative_to(backup_dir)),
                "items": str(items_file.relative_to(backup_dir)),
                "media": str(media_file.relative_to(backup_dir)),
            },
        }
        manifest_file = backup_path / "manifest.json"
        self.save_to_file(manifest, manifest_file)

        return {
            "manifest": manifest_file,
            "item_set": item_set_file,
            "items": items_file,
            "media": media_file,
        }

    def restore_from_backup(
        self, backup_dir: Path | str, dry_run: bool = True
    ) -> dict[str, Any]:
        """
        Restore data from a backup.

        Note: This is a placeholder - actual restoration needs API write access.

        Args:
            backup_dir: Directory containing the backup
            dry_run: If True, only validate the backup without restoring

        Returns:
            Dictionary with restoration status

        Note:
            Actual restoration requires write access to the Omeka S API,
            which may need additional permissions and implementation.
        """
        backup_dir = Path(backup_dir)
        manifest_file = backup_dir / "manifest.json"

        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found in {backup_dir}")

        manifest = self.load_from_file(manifest_file)

        # Validate backup files exist
        for file_type, file_path in manifest["files"].items():
            full_path = backup_dir / file_path
            if not full_path.exists():
                raise FileNotFoundError(f"{file_type} file not found: {full_path}")

        result = {
            "backup_validated": True,
            "item_set_id": manifest["item_set_id"],
            "items_count": manifest["items_count"],
            "media_count": manifest["media_count"],
            "dry_run": dry_run,
            "restored": False,
        }

        if not dry_run:
            result["message"] = (
                "Restoration requires write access to Omeka S API. "
                "This feature needs to be implemented based on your API permissions."
            )

        return result

    # =========================================================================
    # UPDATE OPERATIONS (Placeholders)
    # =========================================================================

    def update_item(
        self, item_id: int, data: dict[str, Any], dry_run: bool = True
    ) -> dict[str, Any]:
        """
        Update an item (placeholder - requires write access).

        Args:
            item_id: The ID of the item to update
            data: The data to update
            dry_run: If True, only validate without updating

        Returns:
            Dictionary with update status
        """
        # Validate the data first
        is_valid, errors = self.validate_item(data)

        result = {
            "item_id": item_id,
            "validation_passed": is_valid,
            "errors": errors,
            "dry_run": dry_run,
            "updated": False,
        }

        if not dry_run and is_valid:
            result["message"] = (
                "Update requires write access to Omeka S API. "
                "This feature needs to be implemented based on your API permissions."
            )

        return result

    def update_media(
        self, media_id: int, data: dict[str, Any], dry_run: bool = True
    ) -> dict[str, Any]:
        """
        Update a media resource (placeholder - requires write access).

        Args:
            media_id: The ID of the media to update
            data: The data to update
            dry_run: If True, only validate without updating

        Returns:
            Dictionary with update status
        """
        # Validate the data first
        is_valid, errors = self.validate_media(data)

        result = {
            "media_id": media_id,
            "validation_passed": is_valid,
            "errors": errors,
            "dry_run": dry_run,
            "updated": False,
        }

        if not dry_run and is_valid:
            result["message"] = (
                "Update requires write access to Omeka S API. "
                "This feature needs to be implemented based on your API permissions."
            )

        return result
