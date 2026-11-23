"""Validate Omeka records without filesystem or network access."""

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

from .models import Item, Media
from .vocabularies import VocabularyLoader

TYPE_LABELS = {"image", "dataset", "interactive resource"}

# Fields without brackets in the datamodel diagram take exactly one value.
# https://dokumentation.stadtgeschichtebasel.ch/products/research-data/datamodel/
SINGLE_VALUE_FIELDS = {
    "Item": (
        "dcterms:identifier",
        "dcterms:title",
        "dcterms:description",
        "dcterms:temporal",
        "dcterms:language",
        "dcterms:isPartOf",
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
            "Invalid type URI (must be Image, Dataset or InteractiveResource)",
        ),
        (
            "language",
            "@value",
            vocabularies.is_valid_language,
            "Invalid language code (not in the DSP language list)",
        ),
    )
    for term, key, valid, message in rules:
        field_name = f"dcterms:{term}"
        values = data.get(field_name)
        if not isinstance(values, list):
            continue
        for index, entry in enumerate(values):
            if isinstance(entry, dict) and term == "language":
                literal = entry.get("@value")
                if not (isinstance(literal, str) and literal):
                    result.errors.append(
                        DataValidationError(
                            resource_type,
                            resource_id,
                            f"{field_name}[{index}]",
                            "Use a literal language code, not a URI: "
                            f"{entry.get('@id') or '(empty)'}",
                        )
                    )
                    continue
            if isinstance(entry, dict) and term == "type" and "@id" not in entry:
                label = entry.get("@value") or entry.get("o:label")
                if isinstance(label, str) and label.casefold() not in TYPE_LABELS:
                    result.errors.append(
                        DataValidationError(
                            resource_type,
                            resource_id,
                            f"{field_name}[{index}]",
                            "Invalid type (must be Image, Dataset or "
                            f"Interactive Resource): {label}",
                        )
                    )
                continue
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
        if not key.startswith("dcterms:") or key == "dcterms:subject":
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


def _is_http_url(text: Any) -> bool:
    if not isinstance(text, str) or any(c.isspace() for c in text):
        return False
    try:
        parts = urlsplit(text)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def _check_invalid_uris(
    result: Findings, data: dict[str, Any], resource_type: str, resource_id: int | str
) -> None:
    """Flag @id values that are not absolute http(s) URLs (issue #57)"""
    for key, value in data.items():
        if key == "dcterms:subject" or not key.startswith("dcterms:"):
            continue
        if not isinstance(value, list):
            continue
        for idx, entry in enumerate(value):
            if not isinstance(entry, dict) or "value_resource_id" in entry:
                continue
            uri = entry.get("@id")
            if not isinstance(uri, str) or _is_http_url(uri):
                continue
            message = f"Invalid URI: {uri[:80]}"
            if _is_http_url(entry.get("o:label")):
                message += " (@id and o:label look swapped)"
            result.errors.append(
                DataValidationError(
                    resource_type, resource_id, f"{key}[{idx}]", message
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
    max_file_size: int | None = 500_000_000,
) -> Findings:
    """Return findings for the supplied records."""
    result = Findings()
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
            _check_invalid_uris(result, record, label, rid)
            size = record.get("o:size")
            if (
                label == "Media"
                and max_file_size
                and isinstance(size, int)
                and size > max_file_size
            ):
                result.warnings.append(
                    DataValidationWarning(
                        "Media",
                        rid,
                        f"File is {size // 1_000_000} MB; DSP conversion may fail "
                        f"above {max_file_size // 1_000_000} MB",
                        "o:size",
                    )
                )
            if label == "Item":
                if check_collection and rid not in parents:
                    result.warnings.append(
                        DataValidationWarning(
                            label, rid, "No media/children found for this item"
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
