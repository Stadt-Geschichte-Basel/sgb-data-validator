"""Data transformation utilities for Omeka S data.

This module provides functions to transform and clean Omeka S data,
including normalization of whitespace characters and other data cleaning operations.
"""

import html
import re
import unicodedata
from copy import deepcopy
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


def normalize_unicode_nfc(text: str) -> str:
    """Normalize Unicode to NFC.

    Applies Canonical Decomposition, followed by Canonical Composition.
    This ensures diacritics like ö, ä, ü are in their composed form.

    Args:
        text: The text to normalize

    Returns:
        The normalized text in NFC form
    """
    if not text:
        return text
    return unicodedata.normalize("NFC", text)


def convert_html_entities(text: str) -> str:
    """Convert HTML entities to their corresponding characters.

    Examples:
        &auml; -> ä
        &ouml; -> ö
        &uuml; -> ü
        &#252; -> ü
        &amp; -> &

    Args:
        text: The text containing HTML entities

    Returns:
        The text with HTML entities converted to characters
    """
    if not text:
        return text
    return html.unescape(text)


def normalize_markdown_links(text: str) -> str:
    """Ensure all Markdown links are in the correct [label](URL) format.

    This function detects and corrects malformed Markdown links including:
    - (URL)[label] -> [label](URL)
    - (label)[URL] -> [label](URL)
    - [URL](label) -> [label](URL)
    - [label] URL -> [label](URL)

    Args:
        text: The text containing Markdown links

    Returns:
        The text with properly formatted Markdown links
    """
    if not text:
        return text

    # Pattern to detect if something looks like a URL
    url_pattern = r"https?://|www\.|[a-z]+\.(com|org|net|de|ch|edu|gov|io|co)"

    # Fix reversed parentheses/brackets: (something)[something_else]
    # Handles both (URL)[label] and (label)[URL]
    def fix_reversed_parens_brackets(match: re.Match[str]) -> str:
        content1 = match.group(1)  # Inside parentheses
        content2 = match.group(2)  # Inside brackets

        # Check which one looks like a URL
        if re.search(url_pattern, content1, re.IGNORECASE):
            # content1 is URL, content2 is label: (URL)[label] -> [label](URL)
            return f"[{content2}]({content1})"
        elif re.search(url_pattern, content2, re.IGNORECASE):
            # content2 is URL, content1 is label: (label)[URL] -> [label](URL)
            return f"[{content1}]({content2})"
        else:
            # Can't determine, keep original
            return match.group(0)

    text = re.sub(r"\(([^)]+)\)\[([^\]]+)\]", fix_reversed_parens_brackets, text)

    # Fix swapped URL/label in standard Markdown: [URL](label) -> [label](URL)
    def fix_swapped_standard_markdown(match: re.Match[str]) -> str:
        content1 = match.group(1)  # Inside brackets
        content2 = match.group(2)  # Inside parentheses

        # Check if they're swapped (URL in brackets, label in parens)
        if re.search(url_pattern, content1, re.IGNORECASE) and not re.search(
            url_pattern, content2, re.IGNORECASE
        ):
            # content1 is URL, content2 is label: [URL](label) -> [label](URL)
            return f"[{content2}]({content1})"
        else:
            # Already correct or can't determine
            return match.group(0)

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", fix_swapped_standard_markdown, text)

    # Fix links with missing brackets: [label] URL -> [label](URL)
    # Match [label] followed by whitespace and a URL not in parentheses
    text = re.sub(r"\[([^\]]+)\]\s+(https?://[^\s\)]+)(?![)])", r"[\1](\2)", text)

    return text


def normalize_abbreviations(text: str) -> str:
    """Normalize common abbreviations to standard forms.

    Replaces:
    - d.j., d. j., D. J. -> d. J.
    - d.ä., d. ä., D. Ä. -> d. Ä.

    Args:
        text: The text containing abbreviations

    Returns:
        The text with normalized abbreviations
    """
    if not text:
        return text

    # Normalize d.j. variations to d. J.
    # Match: d followed by optional period, optional space, j, optional period
    text = re.sub(r"\b[dD]\.?\s*[jJ]\.?(?=\s|$|[^\w])", "d. J.", text)

    # Normalize d.ä. variations to d. Ä.
    # Match: d followed by optional period, optional space, ä/Ä, optional period
    text = re.sub(r"\b[dD]\.?\s*[äÄ]\.?(?=\s|$|[^\w])", "d. Ä.", text)

    return text


def normalize_wikidata_url(text: str) -> str:
    """Convert mobile Wikidata URLs to canonical format.

    Converts:
    - m.wikidata.org/wiki/Q123 -> https://www.wikidata.org/wiki/Q123
    - http://m.wikidata.org/wiki/Q123 -> https://www.wikidata.org/wiki/Q123
    - https://m.wikidata.org/wiki/Q123 -> https://www.wikidata.org/wiki/Q123

    Args:
        text: The text containing Wikidata URLs

    Returns:
        The text with normalized Wikidata URLs
    """
    if not text:
        return text

    # Replace mobile Wikidata URLs with canonical format
    text = re.sub(
        r"(?:https?://)?m\.wikidata\.org/wiki/(Q\d+)",
        r"https://www.wikidata.org/wiki/\1",
        text,
    )

    return text


def normalize_urls(text: str) -> str:
    """Normalize URLs by removing redundant trailing slashes only.

    Per updated requirements: never add a "www." prefix to any domain.
    Specialized canonicalization (e.g. Wikidata mobile -> www.wikidata.org)
    is handled in dedicated functions, not here.

    Args:
        text: The text containing URLs

    Returns:
        The text with normalized URLs
    """
    if not text:
        return text

    # Remove trailing slashes from URLs (except after domain) at token end
    text = re.sub(r"(https?://[^/\s]+)/+(?=\s|$)", r"\1", text)

    return text


def apply_text_transformations(text: str) -> str:
    """Apply all text transformations in the correct order.

    This is the main function that combines all text transformations.

    Args:
        text: The text to transform

    Returns:
        The transformed text
    """
    if not text:
        return text

    # Order matters! Apply transformations in this sequence:
    # 1. Convert HTML entities first (so we can normalize the resulting characters)
    text = convert_html_entities(text)

    # 2. Normalize Unicode to NFC
    text = normalize_unicode_nfc(text)

    # 3. Normalize whitespace
    text = normalize_whitespace(text)

    # 4. Normalize abbreviations
    text = normalize_abbreviations(text)

    # 5. Normalize Markdown links
    text = normalize_markdown_links(text)

    # 6. Normalize Wikidata URLs
    text = normalize_wikidata_url(text)

    # 7. Normalize other URLs
    text = normalize_urls(text)

    return text


def transform_property_value(
    prop: dict[str, Any], apply_all: bool = False
) -> dict[str, Any]:
    """Transform a single Omeka property.

    Args:
        prop: The property dictionary to transform
        apply_all: If True, apply all transformations; if False, only whitespace

    Returns:
        The transformed property
    """
    if not isinstance(prop, dict):
        return prop

    # Only transform literal values (not URIs)
    if prop.get("type") == "literal" and "@value" in prop:
        value = prop["@value"]
        if isinstance(value, str):
            if apply_all:
                normalized = apply_text_transformations(value)
            else:
                normalized = normalize_whitespace(value)
            # Create a new dict to avoid modifying the original
            result = prop.copy()
            result["@value"] = normalized
            return result

    return prop


def transform_item(
    item_data: dict[str, Any], apply_all: bool = False
) -> dict[str, Any]:
    """Transform an item's data by normalizing text in all text fields.

    Args:
        item_data: The item data dictionary
        apply_all: If True, apply all transformations; if False, only whitespace

    Returns:
        A new dictionary with transformed data
    """
    if not isinstance(item_data, dict):
        return item_data

    # Create a copy to avoid modifying the original
    result: dict[str, Any] = {}

    for key, value in item_data.items():
        if key == "o:title" and isinstance(value, str):
            # Transform the title directly
            if apply_all:
                result[key] = apply_text_transformations(value)
            else:
                result[key] = normalize_whitespace(value)
        elif key.startswith("dcterms:") and isinstance(value, list):
            # Transform Dublin Core properties
            result[key] = [
                transform_property_value(prop, apply_all=apply_all) for prop in value
            ]
        else:
            # Keep other fields as-is
            result[key] = value

    return result


INHERITED_MEDIA_FIELDS = ("dcterms:language", "dcterms:temporal")

#: Omeka custom vocabulary used by most existing media dcterms:format values.
FORMAT_VALUE_TEMPLATE = {
    "type": "customvocab:15",
    "property_id": 9,
    "property_label": "Format",
    "is_public": True,
    "@language": "en",
}

# Hyphenated Creative Commons notation ("CC-BY-SA 4.0") -> official ("CC BY-SA 4.0").
_CC_HYPHEN_RE = re.compile(r"\bCC-BY(?=[\s-])")


def fill_media_from_parent(
    media_data: dict[str, Any], parent_item: dict[str, Any] | None
) -> dict[str, Any]:
    """Copy dcterms:language and dcterms:temporal from the parent item.

    Only fills fields that are empty on the media. Never overwrites a value.
    """
    if not parent_item:
        return media_data
    result = dict(media_data)
    for field in INHERITED_MEDIA_FIELDS:
        if not result.get(field) and parent_item.get(field):
            result[field] = [dict(v) for v in parent_item[field]]
    return result


def fill_media_format(
    media_data: dict[str, Any], allowed_mime_types: set[str] | None
) -> dict[str, Any]:
    """Set dcterms:format from o:media_type when dcterms:format is empty.

    Only uses o:media_type values that are in the MIME vocabulary.
    """
    media_type = media_data.get("o:media_type")
    if (
        media_data.get("dcterms:format")
        or not media_type
        or not allowed_mime_types
        or media_type not in allowed_mime_types
    ):
        return media_data
    result = dict(media_data)
    result["dcterms:format"] = [{**FORMAT_VALUE_TEMPLATE, "@value": media_type}]
    return result


def normalize_rights_notation(media_data: dict[str, Any]) -> dict[str, Any]:
    """Write Creative Commons names in dcterms:rights in official notation.

    Example: "CC-BY-SA 4.0, Philippe Saurbeck" -> "CC BY-SA 4.0, Philippe Saurbeck".
    """
    rights = media_data.get("dcterms:rights")
    if not isinstance(rights, list):
        return media_data
    new_rights = []
    changed = False
    for prop in rights:
        value = prop.get("@value") if isinstance(prop, dict) else None
        if isinstance(value, str) and _CC_HYPHEN_RE.search(value):
            prop = {**prop, "@value": _CC_HYPHEN_RE.sub("CC BY", value)}
            changed = True
        new_rights.append(prop)
    if not changed:
        return media_data
    return {**media_data, "dcterms:rights": new_rights}


def transform_media(
    media_data: dict[str, Any],
    apply_all: bool = False,
    parent_item: dict[str, Any] | None = None,
    allowed_mime_types: set[str] | None = None,
) -> dict[str, Any]:
    """Transform a media object's data by normalizing text in all text fields.

    This function also sets o:is_public to False for media with placeholder images.
    With apply_all, it also fills empty fields from context (see Args).

    Args:
        media_data: The media data dictionary
        apply_all: If True, apply all transformations; if False, only whitespace
        parent_item: Parent item; fills empty language/temporal (apply_all only)
        allowed_mime_types: MIME vocabulary; fills empty format (apply_all only)

    Returns:
        A new dictionary with transformed data
    """
    # Media has the same structure as items for the fields we care about
    result = transform_item(media_data, apply_all=apply_all)

    if apply_all:
        result = normalize_rights_notation(result)
        result = fill_media_from_parent(result, parent_item)
        result = fill_media_format(result, allowed_mime_types)

    # Set private flag for media with placeholder images
    result = set_media_private_flag(result)

    return result


def transform_item_set_data(
    item_set_data: dict[str, Any],
    items: list[dict[str, Any]],
    media: list[dict[str, Any]],
    apply_all: bool = False,
    allowed_mime_types: set[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Transform an entire item set with all its items and media.

    This function:
    1. Transforms text in all items and media
    2. Sets o:is_public=False for media with placeholder images
    3. Propagates private flag to items if any of their media children are private

    Args:
        item_set_data: The item set data dictionary
        items: List of item data dictionaries
        media: List of media data dictionaries
        apply_all: If True, apply all transformations; if False, only whitespace

    Returns:
        Tuple of (transformed_item_set, transformed_items, transformed_media),
    """
    # Transform the item set itself (though it usually doesn't have much text)
    transformed_item_set = transform_item(item_set_data, apply_all=apply_all)

    # Transform all items
    transformed_items = [transform_item(item, apply_all=apply_all) for item in items]

    # Transform all media (includes setting private flag for placeholders)
    items_by_id = {i.get("o:id"): i for i in transformed_items}
    transformed_media = [
        transform_media(
            m,
            apply_all=apply_all,
            parent_item=items_by_id.get((m.get("o:item") or {}).get("o:id")),
            allowed_mime_types=allowed_mime_types,
        )
        for m in media
    ]

    # Propagate private flag from media to their parent items
    # If any media child is private, the parent item should also be private
    transformed_items = propagate_private_flag_to_items(
        transformed_items, transformed_media
    )

    return deepcopy((transformed_item_set, transformed_items, transformed_media))


def has_placeholder_media(media_data: dict[str, Any]) -> bool:
    """Recognize the placeholder in Omeka's source name or stored filename."""
    if not isinstance(media_data, dict):
        return False
    return any(
        isinstance(name, str) and "sgb-fdp-platzhalter" in name.lower()
        for name in (media_data.get("o:source"), media_data.get("o:filename"))
    )


def set_media_private_flag(media_data: dict[str, Any]) -> dict[str, Any]:
    """Set o:is_public to False for media with placeholder images.

    This function checks if media contains a placeholder file and sets
    the o:is_public flag to False if it does.

    Args:
        media_data: The media data dictionary

    Returns:
        A copy of the media data with o:is_public potentially updated
    """
    if not isinstance(media_data, dict):
        return media_data

    # Create a copy to avoid modifying the original
    result = media_data.copy()

    # Check if this media has a placeholder
    if has_placeholder_media(media_data):
        result["o:is_public"] = False

    return result


def propagate_private_flag_to_items(
    items: list[dict[str, Any]], media: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Set o:is_public to False for items if any of their media children are private.

    This function creates a mapping of media to their parent items and sets
    items to private if any of their media are private.

    Args:
        items: List of item data dictionaries
        media: List of media data dictionaries

    Returns:
        List of items with o:is_public potentially updated
    """
    if not items or not media:
        return items

    # Build a mapping of item_id -> has_private_media
    item_has_private_media: dict[int, bool] = {}

    for media_item in media:
        if not isinstance(media_item, dict):
            continue

        # Get the parent item ID
        o_item = media_item.get("o:item")
        if not o_item or not isinstance(o_item, dict):
            continue

        item_id = o_item.get("o:id")
        if not item_id:
            continue

        # Check if this media is private
        is_public = media_item.get("o:is_public", True)
        if not is_public:
            item_has_private_media[item_id] = True

    # Update items if they have private media
    result = []
    for item in items:
        if not isinstance(item, dict):
            result.append(item)
            continue

        item_copy = item.copy()
        item_id = item.get("o:id")

        # If this item has any private media, make the item private
        if item_id and item_has_private_media.get(item_id, False):
            item_copy["o:is_public"] = False

        result.append(item_copy)

    return result
