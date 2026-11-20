"""Optional URI checks with a separate unauthenticated client."""

import asyncio
from collections import OrderedDict
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx2

from .validation import DataValidationError, DataValidationWarning, Findings


def extract_uris_from_data(data: dict[str, Any]) -> list[tuple[str, str]]:
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


class LinkChecker:
    def __init__(
        self,
        client: httpx2.AsyncClient,
        result: Findings,
        *,
        check_redirects: bool = False,
        severity: str = "warning",
    ) -> None:
        self.client = client
        self.result = result
        self.check_redirects = check_redirects
        self.uri_check_severity = severity
        self.cache: OrderedDict[str, tuple[int, str | None]] = OrderedDict()

    async def check_single_uri(self, uri: str) -> tuple[int, str | None]:
        if uri in self.cache:
            self.cache.move_to_end(uri)
            return self.cache[uri]
        try:
            response = await self.client.head(uri)
            if response.status_code in (405, 501):
                async with self.client.stream("GET", uri) as response:
                    result = response.status_code, response.headers.get("location")
            else:
                result = response.status_code, response.headers.get("location")
        except (httpx2.RequestError, httpx2.InvalidURL) as exc:
            result = -1, str(exc)
        self.cache[uri] = result
        if len(self.cache) > 10_000:
            self.cache.popitem(last=False)
        return result

    async def check_uri_async(
        self, uri: str, resource_type: str, resource_id: int, field: str
    ) -> None:
        """Check if a URI is reachable asynchronously"""
        if not uri or not uri.startswith(("http://", "https://")):
            return

        self.result.checked_uris += 1
        status_code, redirect_location = await self.check_single_uri(uri)

        if status_code == -1:
            # This was an exception
            self.result.failed_uris += 1
            message = f"URI check failed: {uri} ({redirect_location})"
            if self.uri_check_severity == "error":
                self.result.errors.append(
                    DataValidationError(resource_type, resource_id, field, message)
                )
            else:
                self.result.warnings.append(
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
                    self.result.warnings.append(
                        DataValidationWarning(
                            resource_type, resource_id, f"{field}: {message}"
                        )
                    )

        # Check for HTTP errors
        if status_code >= 400:
            self.result.failed_uris += 1
            message = f"URI returned HTTP {status_code}: {uri}"
            # 404 errors are always treated as errors
            if status_code == 404 or self.uri_check_severity == "error":
                self.result.errors.append(
                    DataValidationError(resource_type, resource_id, field, message)
                )
            else:
                self.result.warnings.append(
                    DataValidationWarning(
                        resource_type, resource_id, f"{field}: {message}"
                    )
                )


async def check_links(
    records: dict[str, list[dict[str, Any]]],
    result: Findings,
    *,
    check_redirects: bool = False,
    severity: str = "warning",
) -> None:
    result.check_uris = True
    headers = {
        "User-Agent": "SGB-Validator/1.0 (+https://github.com/Stadt-Geschichte-Basel/sgb-data-validator)",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
    }
    async with httpx2.AsyncClient(
        timeout=10,
        follow_redirects=False,
        headers=headers,
    ) as client:
        checker = LinkChecker(
            client, result, check_redirects=check_redirects, severity=severity
        )
        for kind, label in (("items", "Item"), ("media", "Media")):
            for record in records[kind]:
                await asyncio.gather(
                    *(
                        checker.check_uri_async(
                            uri, label, record.get("o:id", "unknown"), field
                        )
                        for field, uri in extract_uris_from_data(record)
                    )
                )
