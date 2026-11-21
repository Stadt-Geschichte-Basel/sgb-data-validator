"""Omeka S access through the shared omeka-s-client library."""

from typing import Any

from omeka_s_client import (
    OmekaClient,
    OmekaError,
    OmekaHTTPError,
    Record,
    Upload,
    property_filter,
    property_filters,
)

__all__ = [
    "Omeka",
    "OmekaClient",
    "OmekaError",
    "OmekaHTTPError",
    "Record",
    "Upload",
    "find",
    "optional_get",
]

IDENTIFIER = "dcterms:identifier"


class Omeka(OmekaClient):
    """Open an Omeka client from optional settings and record key presence."""

    def __init__(
        self,
        base_url: str,
        key_identity: str | None = None,
        key_credential: str | None = None,
        *,
        timeout: float = 60,
        **options: Any,
    ) -> None:
        # Unset environment variables can arrive as empty strings.
        super().__init__(
            base_url,
            key_identity=key_identity or None,
            key_credential=key_credential or None,
            timeout=timeout,
            **options,
        )
        self.authenticated = bool(key_identity and key_credential)


def find(
    client: OmekaClient, kind: str, value: str, term: str = IDENTIFIER
) -> list[Record]:
    """List the records with an exact property value."""
    conditions = property_filters(property_filter(term, "eq", value))
    return client.list(kind, filters=conditions, verify=True)


def optional_get(client: OmekaClient, kind: str, rid: int) -> Record | None:
    try:
        return client.get(kind, rid)
    except OmekaHTTPError as exc:
        if exc.status != 404:
            raise
        return None
