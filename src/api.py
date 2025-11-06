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
        self,
        base_url: str,
        key_identity: str | None = None,
        key_credential: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the Omeka API client.

        Args:
            base_url: Base URL of the Omeka S instance
            key_identity: Optional API key identity for authentication
            key_credential: Optional API key credential for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.key_identity = key_identity
        self.key_credential = key_credential
        self.timeout = timeout

        self.client = httpx.Client(timeout=timeout)

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

    def _add_auth_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add authentication parameters if configured."""
        if self.key_identity and self.key_credential:
            params["key_identity"] = self.key_identity
            params["key_credential"] = self.key_credential
        return params

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
        params = self._add_auth_params({})
        response = self.client.get(url, params=params)
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
        params = self._add_auth_params({"page": page, "per_page": per_page, **filters})
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
            params = self._add_auth_params(
                {"item_set_id": item_set_id, "page": page, "per_page": per_page}
            )
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        # Fetch all pages
        items: list[dict[str, Any]] = []
        current_page = 1
        while True:
            url = f"{self.base_url}/api/items"
            params = self._add_auth_params(
                {
                    "item_set_id": item_set_id,
                    "page": current_page,
                    "per_page": per_page,
                }
            )
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
        params = self._add_auth_params({})
        response = self.client.get(url, params=params)
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
        params = self._add_auth_params({})
        response = self.client.get(url, params=params)
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
        params = self._add_auth_params({"item_id": item_id})
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
        Update an item in Omeka S.

        Args:
            item_id: The ID of the item to update
            data: The item data to update
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

        if not is_valid:
            return result

        if dry_run:
            result["message"] = "Dry run - validation passed, no changes made"
            return result

        # Perform the actual update
        url = f"{self.base_url}/api/items/{item_id}"
        params = self._add_auth_params({})

        try:
            response = self.client.put(url, json=data, params=params)
            response.raise_for_status()
            result["updated"] = True
            result["message"] = "Item updated successfully"
        except httpx.HTTPStatusError as e:
            result["message"] = f"Failed to update item: {e}"
        except Exception as e:
            result["message"] = f"Error updating item: {e}"

        return result

    def update_media(
        self, media_id: int, data: dict[str, Any], dry_run: bool = True
    ) -> dict[str, Any]:
        """
        Update a media resource in Omeka S.

        Args:
            media_id: The ID of the media to update
            data: The media data to update
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

        if not is_valid:
            return result

        if dry_run:
            result["message"] = "Dry run - validation passed, no changes made"
            return result

        # Perform the actual update
        url = f"{self.base_url}/api/media/{media_id}"
        params = self._add_auth_params({})

        try:
            response = self.client.put(url, json=data, params=params)
            response.raise_for_status()
            result["updated"] = True
            result["message"] = "Media updated successfully"
        except httpx.HTTPStatusError as e:
            result["message"] = f"Failed to update media: {e}"
        except Exception as e:
            result["message"] = f"Error updating media: {e}"

        return result

    # =========================================================================
    # DOWNLOAD OPERATIONS
    # =========================================================================

    def download_item_set(
        self,
        item_set_id: int,
        output_dir: Path | str,
    ) -> dict[str, Any]:
        """
        Download all items and media in an item set without transformations.

        Downloads raw data from the item set and saves it to files with
        'raw' prefix to indicate untransformed status.

        Args:
            item_set_id: The ID of the item set to download
            output_dir: Directory to save downloaded data

        Returns:
            Dictionary with download summary:
            {
                "item_set_id": int,
                "items_downloaded": int,
                "media_downloaded": int,
                "saved_to": dict,  # file paths
            }
        """
        # Get the item set data
        item_set = self.get_item_set(item_set_id)

        # Get all items and media
        items = self.get_items_from_set(item_set_id)

        # Get all media for all items
        all_media = []
        for item in items:
            item_id = item.get("o:id")
            if item_id:
                media = self.get_media_from_item(item_id)
                all_media.extend(media)

        # Save to files
        output_path = Path(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"raw_itemset_{item_set_id}_{timestamp}"
        download_dir = output_path / dir_name
        download_dir.mkdir(parents=True, exist_ok=True)

        # Save raw data (status indicated in filenames)
        item_set_file = download_dir / "item_set_raw.json"
        items_file = download_dir / "items_raw.json"
        media_file = download_dir / "media_raw.json"

        self.save_to_file(item_set, item_set_file)
        self.save_to_file(items, items_file)
        self.save_to_file(all_media, media_file)

        # Save download metadata
        metadata = {
            "item_set_id": item_set_id,
            "timestamp": timestamp,
            "status": "raw",
            "items_count": len(items),
            "media_count": len(all_media),
            "files": {
                "item_set": str(item_set_file.relative_to(output_path)),
                "items": str(items_file.relative_to(output_path)),
                "media": str(media_file.relative_to(output_path)),
            },
        }
        metadata_file = download_dir / "download_metadata.json"
        self.save_to_file(metadata, metadata_file)

        return {
            "item_set_id": item_set_id,
            "items_downloaded": len(items),
            "media_downloaded": len(all_media),
            "saved_to": {
                "directory": download_dir,
                "item_set": item_set_file,
                "items": items_file,
                "media": media_file,
                "metadata": metadata_file,
            },
        }

    # =========================================================================
    # TRANSFORMATION OPERATIONS
    # =========================================================================

    def apply_transformations(
        self,
        input_dir: Path | str,
        output_dir: Path | str | None = None,
        apply_whitespace_normalization: bool = True,
    ) -> dict[str, Any]:
        """
        Apply transformations to downloaded data files.

        Loads data from input files, applies transformations,
        and saves transformed data to output files with 'transformed' prefix.

        Args:
            input_dir: Directory containing raw data files (items.json, media.json)
            output_dir: Directory to save transformed data.
                       If None, saves in parent directory of input_dir.
            apply_whitespace_normalization: Apply whitespace normalization
                (default: True)

        Returns:
            Dictionary with transformation summary:
            {
                "items_transformed": int,
                "media_transformed": int,
                "transformations_applied": list[str],
                "saved_to": dict,  # file paths
            }
        """
        from src.transformations import transform_item_set_data

        input_path = Path(input_dir)

        # Load raw data from files (support multiple naming conventions)
        # Prefer explicitly suffixed raw files, then generic names
        item_set_file = (
            input_path / "item_set_raw.json"
            if (input_path / "item_set_raw.json").exists()
            else input_path / "item_set.json"
        )
        items_file = (
            input_path / "items_raw.json"
            if (input_path / "items_raw.json").exists()
            else input_path / "items.json"
        )
        media_file = (
            input_path / "media_raw.json"
            if (input_path / "media_raw.json").exists()
            else input_path / "media.json"
        )

        if not items_file.exists():
            raise FileNotFoundError(f"Items file not found: {items_file}")

        # Load the data
        item_set = self.load_from_file(item_set_file) if item_set_file.exists() else {}
        items = self.load_from_file(items_file)
        all_media = self.load_from_file(media_file) if media_file.exists() else []

        # Ensure items and media are lists
        if not isinstance(items, list):
            items = [items]
        if not isinstance(all_media, list):
            all_media = [all_media]

        # Load metadata to get item_set_id
        metadata_file = input_path / "download_metadata.json"
        item_set_id = None
        if metadata_file.exists():
            metadata = self.load_from_file(metadata_file)
            item_set_id = metadata.get("item_set_id")
        else:
            # Try to get from item_set data
            item_set_id = item_set.get("o:id") if item_set else None

        # Apply transformations
        transformations_applied = []
        if apply_whitespace_normalization:
            item_set, items, all_media = transform_item_set_data(
                item_set, items, all_media
            )
            transformations_applied.append("whitespace_normalization")

        # Determine output directory
        if output_dir is None:
            output_path = input_path.parent
        else:
            output_path = Path(output_dir)

        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if item_set_id:
            dir_name = f"transformed_itemset_{item_set_id}_{timestamp}"
        else:
            dir_name = f"transformed_{timestamp}"
        transform_dir = output_path / dir_name
        transform_dir.mkdir(parents=True, exist_ok=True)

        # Save transformed data
        # Use suffixed filenames to indicate transformed status
        out_item_set_file = transform_dir / "item_set_transformed.json"
        out_items_file = transform_dir / "items_transformed.json"
        out_media_file = transform_dir / "media_transformed.json"

        if item_set:
            self.save_to_file(item_set, out_item_set_file)
        self.save_to_file(items, out_items_file)
        self.save_to_file(all_media, out_media_file)

        # Save transformation metadata
        metadata = {
            "item_set_id": item_set_id,
            "timestamp": timestamp,
            "status": "transformed",
            "source_directory": str(input_path),
            "items_count": len(items),
            "media_count": len(all_media),
            "transformations_applied": transformations_applied,
            "files": {
                "item_set": str(out_item_set_file.relative_to(output_path)),
                "items": str(out_items_file.relative_to(output_path)),
                "media": str(out_media_file.relative_to(output_path)),
            },
        }
        metadata_file = transform_dir / "transformation_metadata.json"
        self.save_to_file(metadata, metadata_file)

        return {
            "items_transformed": len(items),
            "media_transformed": len(all_media),
            "transformations_applied": transformations_applied,
            "saved_to": {
                "directory": transform_dir,
                "item_set": out_item_set_file if item_set else None,
                "items": out_items_file,
                "media": out_media_file,
                "metadata": metadata_file,
            },
        }

    # =========================================================================
    # OFFLINE FILE OPERATIONS
    # =========================================================================

    def validate_offline_files(self, directory: Path | str) -> dict[str, Any]:
        """
        Validate transformed data from offline JSON files.

        Args:
            directory: Directory containing the transformed data files
                      (items.json, media.json, and optionally item_set.json)

        Returns:
            Dictionary with validation results:
            {
                "items_validated": int,
                "items_valid": int,
                "items_errors": list[dict],
                "media_validated": int,
                "media_valid": int,
                "media_errors": list[dict],
                "overall_valid": bool,
            }
        """
        directory = Path(directory)

        result = {
            "items_validated": 0,
            "items_valid": 0,
            "items_errors": [],
            "media_validated": 0,
            "media_valid": 0,
            "media_errors": [],
            "overall_valid": True,
        }

        # Helper to choose among multiple candidate filenames
        def choose_file(dirpath: Path, candidates: list[str]) -> Path | None:
            for name in candidates:
                p = dirpath / name
                if p.exists():
                    return p
            return None

        # Validate items
        items_file = choose_file(
            directory,
            [
                "items_transformed.json",
                "items.json",
                "items_raw.json",
            ],
        )
        if items_file and items_file.exists():
            items = self.load_from_file(items_file)
            if not isinstance(items, list):
                items = [items]

            for item in items:
                result["items_validated"] += 1
                is_valid, errors = self.validate_item(item)
                if is_valid:
                    result["items_valid"] += 1
                else:
                    result["overall_valid"] = False
                    result["items_errors"].append(
                        {
                            "item_id": item.get("o:id"),
                            "errors": errors,
                        }
                    )

        # Validate media
        media_file = choose_file(
            directory,
            [
                "media_transformed.json",
                "media.json",
                "media_raw.json",
            ],
        )
        if media_file and media_file.exists():
            media_list = self.load_from_file(media_file)
            if not isinstance(media_list, list):
                media_list = [media_list]

            for media in media_list:
                result["media_validated"] += 1
                is_valid, errors = self.validate_media(media)
                if is_valid:
                    result["media_valid"] += 1
                else:
                    result["overall_valid"] = False
                    result["media_errors"].append(
                        {
                            "media_id": media.get("o:id"),
                            "errors": errors,
                        }
                    )

        return result

    def upload_transformed_data(
        self,
        directory: Path | str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """
        Upload transformed data from offline files back to Omeka S.

        Args:
            directory: Directory containing the transformed data files
            dry_run: If True, only validate without uploading (default: True)

        Returns:
            Dictionary with upload results:
            {
                "items_processed": int,
                "items_updated": int,
                "items_failed": int,
                "media_processed": int,
                "media_updated": int,
                "media_failed": int,
                "errors": list[dict],
                "dry_run": bool,
            }
        """
        directory = Path(directory)

        result = {
            "items_processed": 0,
            "items_updated": 0,
            "items_failed": 0,
            "media_processed": 0,
            "media_updated": 0,
            "media_failed": 0,
            "errors": [],
            "dry_run": dry_run,
        }

        # First validate all files
        validation = self.validate_offline_files(directory)
        if not validation["overall_valid"]:
            result["errors"].append(
                {
                    "type": "validation_failed",
                    "message": "Validation failed - cannot proceed with upload",
                    "validation_errors": {
                        "items": validation["items_errors"],
                        "media": validation["media_errors"],
                    },
                }
            )
            return result

        # Helper to choose among multiple candidate filenames
        def choose_file(dirpath: Path, candidates: list[str]) -> Path | None:
            for name in candidates:
                p = dirpath / name
                if p.exists():
                    return p
            return None

        # Upload items
        items_file = choose_file(
            directory,
            [
                "items_transformed.json",
                "items.json",
                "items_raw.json",
            ],
        )
        if items_file and items_file.exists():
            items = self.load_from_file(items_file)
            if not isinstance(items, list):
                items = [items]

            for item in items:
                result["items_processed"] += 1
                item_id = item.get("o:id")
                if not item_id:
                    result["items_failed"] += 1
                    result["errors"].append(
                        {
                            "type": "item",
                            "message": "Item missing o:id field",
                        }
                    )
                    continue

                update_result = self.update_item(item_id, item, dry_run=dry_run)
                if update_result["updated"] or (
                    dry_run and update_result["validation_passed"]
                ):
                    result["items_updated"] += 1
                else:
                    result["items_failed"] += 1
                    result["errors"].append(
                        {
                            "type": "item",
                            "item_id": item_id,
                            "message": update_result.get("message", "Unknown error"),
                        }
                    )

        # Upload media
        media_file = choose_file(
            directory,
            [
                "media_transformed.json",
                "media.json",
                "media_raw.json",
            ],
        )
        if media_file and media_file.exists():
            media_list = self.load_from_file(media_file)
            if not isinstance(media_list, list):
                media_list = [media_list]

            for media in media_list:
                result["media_processed"] += 1
                media_id = media.get("o:id")
                if not media_id:
                    result["media_failed"] += 1
                    result["errors"].append(
                        {
                            "type": "media",
                            "message": "Media missing o:id field",
                        }
                    )
                    continue

                update_result = self.update_media(media_id, media, dry_run=dry_run)
                if update_result["updated"] or (
                    dry_run and update_result["validation_passed"]
                ):
                    result["media_updated"] += 1
                else:
                    result["media_failed"] += 1
                    result["errors"].append(
                        {
                            "type": "media",
                            "media_id": media_id,
                            "message": update_result.get("message", "Unknown error"),
                        }
                    )

        return result
