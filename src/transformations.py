"""Data transformation utilities for Omeka S data.

This module provides functions to transform and clean Omeka S data,
including normalization of whitespace characters and other data cleaning operations.
"""

import asyncio
import html
import re
import unicodedata
from typing import Any

import httpx


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


async def check_https_available(url: str, timeout: float = 5.0) -> bool:
    """Check if HTTPS version of an HTTP URL is available.

    Args:
        url: The HTTP URL to check
        timeout: Request timeout in seconds

    Returns:
        True if HTTPS version is available and responds with 2xx or 3xx status,
        False otherwise
    """
    if not url.startswith("http://"):
        return False

    https_url = url.replace("http://", "https://", 1)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.head(https_url)
            # Consider 2xx and 3xx as success
            return 200 <= response.status_code < 400
    except (httpx.RequestError, httpx.HTTPError):
        # If HTTPS fails, keep HTTP
        return False


async def upgrade_http_to_https_async(text: str) -> str:
    """Upgrade HTTP URLs to HTTPS where available (async version).

    Finds all HTTP URLs in the text and checks if HTTPS is available.
    If HTTPS works, replaces the HTTP URL with the HTTPS version.

    Args:
        text: The text containing URLs

    Returns:
        The text with HTTP URLs upgraded to HTTPS where possible
    """
    if not text:
        return text

    # Find all HTTP URLs (not already HTTPS)
    http_urls = re.findall(r"http://[^\s<>\[\]{}|\\^`]+", text)

    if not http_urls:
        return text

    # Check all URLs concurrently
    checks = [check_https_available(url) for url in http_urls]
    results = await asyncio.gather(*checks)

    # Replace HTTP with HTTPS for URLs where HTTPS is available
    for url, https_available in zip(http_urls, results, strict=True):
        if https_available:
            https_url = url.replace("http://", "https://", 1)
            text = text.replace(url, https_url)

    return text


def upgrade_http_to_https(text: str) -> str:
    """Upgrade HTTP URLs to HTTPS where available (sync wrapper).

    This is a synchronous wrapper around upgrade_http_to_https_async.
    Use this in non-async contexts.

    Args:
        text: The text containing URLs

    Returns:
        The text with HTTP URLs upgraded to HTTPS where possible
    """
    if not text:
        return text

    # Run the async function in an event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, create a new one
            import threading

            result = [text]

            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result[0] = new_loop.run_until_complete(
                    upgrade_http_to_https_async(text)
                )
                new_loop.close()

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            return result[0]
        else:
            return loop.run_until_complete(upgrade_http_to_https_async(text))
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(upgrade_http_to_https_async(text))


def apply_text_transformations(text: str, upgrade_https: bool = True) -> str:
    """Apply all text transformations in the correct order.

    This is the main function that combines all text transformations.

    Args:
        text: The text to transform
        upgrade_https: If True, upgrade HTTP URLs to HTTPS where available

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

    # 7. Upgrade HTTP to HTTPS where available (before URL normalization)
    if upgrade_https:
        text = upgrade_http_to_https(text)

    # 8. Normalize other URLs
    text = normalize_urls(text)

    return text


def transform_property_value(
    prop: dict[str, Any], apply_all: bool = False, upgrade_https: bool = True
) -> dict[str, Any]:
    """Transform a single Omeka property.

    Args:
        prop: The property dictionary to transform
        apply_all: If True, apply all transformations; if False, only whitespace
        upgrade_https: If True, upgrade HTTP URLs to HTTPS where available

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
                normalized = apply_text_transformations(
                    value, upgrade_https=upgrade_https
                )
            else:
                normalized = normalize_whitespace(value)
            # Create a new dict to avoid modifying the original
            result = prop.copy()
            result["@value"] = normalized
            return result

    return prop


def transform_item(
    item_data: dict[str, Any], apply_all: bool = False, upgrade_https: bool = True
) -> dict[str, Any]:
    """Transform an item's data by normalizing text in all text fields.

    Args:
        item_data: The item data dictionary
        apply_all: If True, apply all transformations; if False, only whitespace
        upgrade_https: If True, upgrade HTTP URLs to HTTPS where available

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
            if apply_all:
                result[key] = apply_text_transformations(
                    value, upgrade_https=upgrade_https
                )
            else:
                result[key] = normalize_whitespace(value)
        elif key.startswith("dcterms:") and isinstance(value, list):
            # Transform Dublin Core properties
            result[key] = [
                transform_property_value(
                    prop, apply_all=apply_all, upgrade_https=upgrade_https
                )
                for prop in value
            ]
        else:
            # Keep other fields as-is
            result[key] = value

    return result


def transform_media(
    media_data: dict[str, Any], apply_all: bool = False, upgrade_https: bool = True
) -> dict[str, Any]:
    """Transform a media object's data by normalizing text in all text fields.

    Args:
        media_data: The media data dictionary
        apply_all: If True, apply all transformations; if False, only whitespace
        upgrade_https: If True, upgrade HTTP URLs to HTTPS where available

    Returns:
        A new dictionary with transformed data
    """
    # Media has the same structure as items for the fields we care about
    return transform_item(media_data, apply_all=apply_all, upgrade_https=upgrade_https)


def transform_item_set_data(
    item_set_data: dict[str, Any],
    items: list[dict[str, Any]],
    media: list[dict[str, Any]],
    apply_all: bool = False,
    upgrade_https: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Transform an entire item set with all its items and media.

    Args:
        item_set_data: The item set data dictionary
        items: List of item data dictionaries
        media: List of media data dictionaries
        apply_all: If True, apply all transformations; if False, only whitespace
        upgrade_https: If True, upgrade HTTP URLs to HTTPS where available

    Returns:
        Tuple of (transformed_item_set, transformed_items, transformed_media)
    """
    # Transform the item set itself (though it usually doesn't have much text)
    transformed_item_set = transform_item(
        item_set_data, apply_all=apply_all, upgrade_https=upgrade_https
    )

    # Transform all items
    transformed_items = [
        transform_item(item, apply_all=apply_all, upgrade_https=upgrade_https)
        for item in items
    ]

    # Transform all media
    transformed_media = [
        transform_media(m, apply_all=apply_all, upgrade_https=upgrade_https)
        for m in media
    ]

    return transformed_item_set, transformed_items, transformed_media


def has_placeholder_media(media_data: dict[str, Any]) -> bool:
    """Check if media contains sgb-fdp-platzhalter in o:filename.

    This function identifies media that should be marked as private.

    Args:
        media_data: The media data dictionary

    Returns:
        True if the media contains a placeholder file, False otherwise
    """
    if not isinstance(media_data, dict):
        return False

    filename = media_data.get("o:filename", "")
    if isinstance(filename, str):
        return "sgb-fdp-platzhalter" in filename.lower()

    return False


def extract_wikidata_qids(text: str) -> list[str]:
    """Extract all Wikidata QIDs from text.

    Args:
        text: The text to search for QIDs

    Returns:
        List of unique QIDs found in the text
    """
    if not text:
        return []

    # Match Q followed by digits (Wikidata item identifiers)
    qids = re.findall(r"\bQ\d+\b", text)

    # Return unique QIDs in order of appearance
    seen = set()
    unique_qids = []
    for qid in qids:
        if qid not in seen:
            seen.add(qid)
            unique_qids.append(qid)

    return unique_qids


def deduplicate_qids(qids: list[str]) -> list[str]:
    """Remove duplicate QIDs while preserving order.

    Args:
        qids: List of QIDs (may contain duplicates)

    Returns:
        List of unique QIDs in order of first appearance
    """
    seen = set()
    result = []
    for qid in qids:
        if qid not in seen:
            seen.add(qid)
            result.append(qid)
    return result


def normalize_name(name: str) -> str:
    """Normalize a name for deduplication.

    This function normalizes names by:
    - Converting to lowercase
    - Removing extra whitespace
    - Applying Unicode NFC normalization

    Args:
        name: The name to normalize

    Returns:
        The normalized name
    """
    if not name:
        return ""

    # Apply text transformations
    name = apply_text_transformations(name)

    # Convert to lowercase for case-insensitive comparison
    name = name.lower()

    return name
