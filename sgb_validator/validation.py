"""Validate Omeka records without filesystem or network access."""

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from .models import Item, Media
from .vocabularies import VocabularyLoader

# Fields without brackets in the datamodel diagram take exactly one value.
# https://dokumentation.stadtgeschichtebasel.ch/products/research-data/datamodel/
SINGLE_VALUE_FIELDS = {
    "Item": (
        "dcterms:identifier",
        "dcterms:title",
        "dcterms:description",
        "dcterms:temporal",
        "dcterms:language",
    ),
    "Media": (
        "dcterms:identifier",
        "dcterms:title",
        "dcterms:description",
        "dcterms:date",
        "dcterms:temporal",
        "dcterms:type",
        "dcterms:format",
        "dcterms:extent",
        "dcterms:language",
        "dcterms:rights",
        "dcterms:license",
    ),
}


@dataclass(frozen=True)
class DataValidationError:
    resource_type: str
    resource_id: int | str
    field: str
    error: str

    def __str__(self) -> str:
        return f"[{self.resource_type} {self.resource_id}] {self.field}: {self.error}"


@dataclass(frozen=True)
class DataValidationWarning:
    resource_type: str
    resource_id: int | str
    message: str
    field: str | None = None

    def __str__(self) -> str:
        prefix = f"{self.field}: " if self.field else ""
        return f"[{self.resource_type} {self.resource_id}] {prefix}{self.message}"


@dataclass
class Findings:
    errors: list[DataValidationError] = field(default_factory=list)
    warnings: list[DataValidationWarning] = field(default_factory=list)
    validated_items: int = 0
    validated_media: int = 0
    checked_uris: int = 0
    failed_uris: int = 0
    check_uris: bool = False


def _validate_vocabularies(
    vocabularies: VocabularyLoader,
    result: Findings,
    data: dict[str, Any],
    resource_type: str,
    resource_id: int | str,
) -> None:
    """Validate vocabulary-controlled fields"""
    for field_name in SINGLE_VALUE_FIELDS.get(resource_type, ()):
        values = data.get(field_name)
        if isinstance(values, list) and len(values) > 1:
            result.errors.append(
                DataValidationError(
                    resource_type,
                    resource_id,
                    field_name,
                    f"Only one value allowed, found {len(values)}",
                )
            )

    rules = (
        (
            "temporal",
            "@value",
            vocabularies.is_valid_era,
            "Value must be from Era vocabulary",
        ),
        (
            "format",
            "@value",
            vocabularies.is_valid_mime_type,
            "Value must be from MIME type vocabulary",
        ),
        ("license", "@value", vocabularies.is_valid_license, "Invalid license URI"),
        (
            "type",
            "@id",
            vocabularies.is_valid_type,
            "Invalid type URI (must be Image or Dataset)",
        ),
        (
            "language",
            "@value",
            vocabularies.is_valid_language,
            "Invalid language code (must be valid ISO 639-1 two-letter code)",
        ),
        (
            "subject",
            "@value",
            lambda text: not text[0].isdigit() or vocabularies.is_valid_iconclass(text),
            "Invalid Iconclass code",
        ),
    )
    for term, key, valid, message in rules:
        field_name = f"dcterms:{term}"
        values = data.get(field_name)
        if not isinstance(values, list):
            continue
        for index, entry in enumerate(values):
            value = entry.get(key) if isinstance(entry, dict) else None
            if isinstance(value, str) and value and not valid(value):
                result.errors.append(
                    DataValidationError(
                        resource_type,
                        resource_id,
                        f"{field_name}[{index}]",
                        f"{message}: {value}",
                    )
                )


def _check_missing_field(data: dict[str, Any], field_name: str) -> bool:
    """Check if a field is missing or empty"""
    value = data.get(field_name)
    if value is None:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def _check_thumbnail_or_media(data: dict[str, Any]) -> bool:
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


def _contains_url(text: str) -> bool:
    """Check if text contains a URL pattern

    Detects URLs starting with http://, https://, ftp://, or www.
    """
    if not text or not isinstance(text, str):
        return False

    # Pattern to match common URL formats
    url_pattern = r"(?:https?://|ftp://|www\.)[^\s]+"
    return bool(re.search(url_pattern, text, re.IGNORECASE))


def _check_literal_fields_for_urls(
    result: Findings, data: dict[str, Any], resource_type: str, resource_id: int | str
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
                        if field_value and _contains_url(field_value):
                            display_value = field_value[:80]
                            if len(field_value) > 80:
                                display_value += "..."
                            result.warnings.append(
                                DataValidationWarning(
                                    resource_type,
                                    resource_id,
                                    f"{key}[{idx}]: Literal field contains "
                                    f"URL: {display_value}",
                                )
                            )


REQUIRED_TERMS = {
    "Item": ("identifier", "description", "temporal"),
    "Media": ("identifier", "description", "rights", "license"),
}
RECOMMENDED_TERMS = {
    "Item": ("language", "isPartOf"),
    "Media": (
        "creator",
        "publisher",
        "temporal",
        "type",
        "format",
        "extent",
        "source",
        "language",
    ),
}


def _validate_fields(
    result: Findings,
    record: dict[str, Any],
    label: str,
    rid: int | str,
) -> None:
    if not record.get("o:title"):
        result.errors.append(
            DataValidationError(label, rid, "o:title", "Field is required")
        )
    for term in REQUIRED_TERMS[label]:
        name = f"dcterms:{term}"
        if _check_missing_field(record, name):
            result.errors.append(
                DataValidationError(label, rid, name, "Field is required")
            )
    if label == "Media":
        template = record.get("o:resource_template") or {}
        if not (template.get("@id") or template.get("o:id")):
            result.warnings.append(
                DataValidationWarning(
                    label,
                    rid,
                    "Missing o:resource_template (@id and o:id)",
                )
            )
    if _check_thumbnail_or_media(record):
        result.warnings.append(
            DataValidationWarning(
                label,
                rid,
                "Missing thumbnails (large, medium, small) or media",
            )
        )
    for term in RECOMMENDED_TERMS[label]:
        name = f"dcterms:{term}"
        if _check_missing_field(record, name):
            result.warnings.append(DataValidationWarning(label, rid, f"Missing {name}"))


def validate_records(
    items: list[dict[str, Any]],
    media: list[dict[str, Any]],
    vocabularies: VocabularyLoader,
    *,
    check_collection: bool = True,
) -> Findings:
    """Return findings for the supplied records."""
    from .transformations import has_placeholder_media

    result = Findings()
    items_by_id = {
        item["o:id"]: item for item in items if isinstance(item.get("o:id"), int)
    }
    parents = {
        m["o:item"]["o:id"]: m
        for m in media
        if isinstance(m.get("o:item"), dict)
        and isinstance(m["o:item"].get("o:id"), int)
    }
    for label, records, model in (
        ("Item", items, Item),
        ("Media", media, Media),
    ):
        identifiers: dict[str, list[int | str]] = {}
        for record in records:
            raw_id = record.get("o:id")
            rid = raw_id if isinstance(raw_id, int) else "unknown"
            values = record.get("dcterms:identifier")
            if isinstance(values, list):
                distinct = {
                    value["@value"]
                    for value in values
                    if isinstance(value, dict)
                    and isinstance(value.get("@value"), str)
                    and value["@value"]
                }
                for identifier in sorted(distinct):
                    identifiers.setdefault(identifier, []).append(rid)
            try:
                model.model_validate(record)
            except ValidationError as exc:
                for error in exc.errors():
                    name = ".".join(str(loc) for loc in error["loc"])
                    result.errors.append(
                        DataValidationError(label, rid, name, error["msg"])
                    )
                continue
            if label == "Item":
                result.validated_items += 1
            else:
                result.validated_media += 1
            _validate_vocabularies(vocabularies, result, record, label, rid)
            _validate_fields(result, record, label, rid)
            _check_literal_fields_for_urls(result, record, label, rid)
            if label == "Item":
                if check_collection and rid not in parents:
                    result.warnings.append(
                        DataValidationWarning(
                            label, rid, "No media/children found for this item"
                        )
                    )
            else:
                placeholder = has_placeholder_media(record)
                parent = items_by_id.get((record.get("o:item") or {}).get("o:id"))
                if placeholder and record.get("o:is_public", True):
                    result.warnings.append(
                        DataValidationWarning(
                            label,
                            rid,
                            "Placeholder media must be private",
                            "o:is_public",
                        )
                    )
                if (
                    (placeholder or record.get("o:is_public") is False)
                    and parent is not None
                    and parent.get("o:is_public", True)
                ):
                    result.warnings.append(
                        DataValidationWarning(
                            "Item",
                            parent["o:id"],
                            f"Media {rid} is private or a placeholder. "
                            "Set its parent to private.",
                            "o:is_public",
                        )
                    )
        for identifier, ids in identifiers.items():
            if len(ids) > 1:
                for rid in ids:
                    group = "items" if label == "Item" else "media"
                    result.errors.append(
                        DataValidationError(
                            label,
                            rid,
                            "dcterms:identifier",
                            f"Duplicate identifier '{identifier}' "
                            f"found in {group}: {ids}",
                        )
                    )
    return result
