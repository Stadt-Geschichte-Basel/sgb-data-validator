"""Data transformation utilities for Omeka S data.

This module provides functions to transform and clean Omeka S data,
including normalization of whitespace characters and other data cleaning operations.
"""

import re
from typing import Any


def normalize_whitespace(text: str) -> str:
    """Normalize non-standard whitespace characters in text.

    Replaces various Unicode whitespace and control characters with standard spaces:
    - Non-breaking spaces (U+00A0, U+202F, etc.)
    - Zero-width spaces (U+200B, U+200C, U+200D, U+FEFF)
    - Soft hyphens (U+00AD)
    - Line/paragraph separators (U+2028, U+2029)
    - Directional formatting (U+202A, U+202B, U+202C, U+202D, U+202E)
    - Various other Unicode whitespace characters

    Also normalizes:
    - Multiple consecutive spaces to single space
    - Line breaks to single newline
    - Removes trailing/leading whitespace from each line

    Args:
        text: The text to normalize

    Returns:
        The normalized text with standard whitespace
    """
    if not text:
        return text

    # Replace soft hyphens with empty string (they're optional hyphens)
    text = text.replace("\u00ad", "")

    # Replace various non-breaking spaces with regular space
    text = text.replace("\u00a0", " ")  # Non-breaking space
    text = text.replace("\u202f", " ")  # Narrow no-break space
    text = text.replace("\u2007", " ")  # Figure space
    text = text.replace("\u2060", "")  # Word joiner (zero-width)

    # Replace zero-width characters with empty string
    text = text.replace("\u200b", "")  # Zero-width space
    text = text.replace("\u200c", "")  # Zero-width non-joiner
    text = text.replace("\u200d", "")  # Zero-width joiner
    text = text.replace("\ufeff", "")  # Zero-width no-break space (BOM)

    # Remove directional formatting characters
    text = text.replace("\u202a", "")  # Left-to-right embedding
    text = text.replace("\u202b", "")  # Right-to-left embedding
    text = text.replace("\u202c", "")  # Pop directional formatting
    text = text.replace("\u202d", "")  # Left-to-right override
    text = text.replace("\u202e", "")  # Right-to-left override

    # Replace line/paragraph separators with newline
    text = text.replace("\u2028", "\n")  # Line separator
    text = text.replace("\u2029", "\n")  # Paragraph separator

    # Normalize other Unicode spaces to regular space
    # This includes em space, en space, thin space, hair space, etc.
    text = re.sub(r"[\u2000-\u200A]", " ", text)

    # Normalize tabs to spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)

    # Normalize multiple newlines to maximum of two (preserves paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove trailing whitespace from each line while preserving line breaks
    lines = text.split("\n")
    text = "\n".join(line.rstrip() for line in lines)

    # Remove leading/trailing whitespace from the entire text
    text = text.strip()

    return text


def transform_property_value(prop: dict[str, Any]) -> dict[str, Any]:
    """Transform a single Omeka property.

    Args:
        prop: The property dictionary to transform

    Returns:
        The transformed property
    """
    if not isinstance(prop, dict):
        return prop

    # Only transform literal values (not URIs)
    if prop.get("type") == "literal" and "@value" in prop:
        value = prop["@value"]
        if isinstance(value, str):
            normalized = normalize_whitespace(value)
            # Create a new dict to avoid modifying the original
            result = prop.copy()
            result["@value"] = normalized
            return result

    return prop


def transform_item(item_data: dict[str, Any]) -> dict[str, Any]:
    """Transform an item's data by normalizing whitespace in all text fields.

    Args:
        item_data: The item data dictionary

    Returns:
        A new dictionary with transformed data
    """
    if not isinstance(item_data, dict):
        return item_data

    # Create a copy to avoid modifying the original
    result = {}

    for key, value in item_data.items():
        if key == "o:title" and isinstance(value, str):
            # Transform the title directly
            result[key] = normalize_whitespace(value)
        elif key.startswith("dcterms:") and isinstance(value, list):
            # Transform Dublin Core properties
            result[key] = [transform_property_value(prop) for prop in value]
        else:
            # Keep other fields as-is
            result[key] = value

    return result


def transform_media(media_data: dict[str, Any]) -> dict[str, Any]:
    """Transform a media object's data by normalizing whitespace in all text fields.

    Args:
        media_data: The media data dictionary

    Returns:
        A new dictionary with transformed data
    """
    # Media has the same structure as items for the fields we care about
    return transform_item(media_data)


def transform_item_set_data(
    item_set_data: dict[str, Any],
    items: list[dict[str, Any]],
    media: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Transform an entire item set with all its items and media.

    Args:
        item_set_data: The item set data dictionary
        items: List of item data dictionaries
        media: List of media data dictionaries

    Returns:
        Tuple of (transformed_item_set, transformed_items, transformed_media)
    """
    # Transform the item set itself (though it usually doesn't have much text)
    transformed_item_set = transform_item(item_set_data)

    # Transform all items
    transformed_items = [transform_item(item) for item in items]

    # Transform all media
    transformed_media = [transform_media(m) for m in media]

    return transformed_item_set, transformed_items, transformed_media
