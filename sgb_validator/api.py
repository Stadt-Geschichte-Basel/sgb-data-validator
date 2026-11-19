"""HTTP access to an Omeka S instance."""

import json
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any

import httpx2

Record = dict[str, Any]


class _RedactAPIQuery(logging.Filter):
    """Remove Omeka query credentials from HTTPX2 request logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                value.copy_remove_param("key_identity").copy_remove_param(
                    "key_credential"
                )
                if isinstance(value, httpx2.URL)
                else value
                for value in record.args
            )
        return True


logging.getLogger("httpx2").addFilter(_RedactAPIQuery())


class OmekaError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class OmekaAPI:
    def __init__(
        self,
        base_url: str,
        key_identity: str | None = None,
        key_credential: str | None = None,
        *,
        timeout: float = 60,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        url = httpx2.URL(base_url)
        if url.scheme not in ("https", "http") or not url.host:
            raise ValueError("Set OMEKA_URL to an HTTP or HTTPS Omeka instance URL")
        if url.userinfo or url.query or url.fragment:
            raise ValueError("Use an Omeka URL without credentials, query, or fragment")
        if bool(key_identity) != bool(key_credential):
            raise ValueError("Supply both Omeka key identity and credential")
        self.base_url = str(url).rstrip("/").removesuffix("/api")
        self.auth = (
            {"key_identity": key_identity, "key_credential": key_credential}
            if key_identity and key_credential
            else {}
        )
        self.client = httpx2.Client(
            timeout=timeout,
            transport=transport,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        )

    def __enter__(self) -> "OmekaAPI":
        return self

    def __exit__(self, *_: Any) -> None:
        self.client.close()

    def request(
        self, method: str, endpoint: str, *, params: Record | None = None, **kwargs: Any
    ) -> httpx2.Response:
        if method != "GET" and not self.auth:
            raise OmekaError("Omeka credentials are required for writes")
        attempts = 4 if method == "GET" else 1
        for attempt in range(attempts):
            query = {**(params or {}), **self.auth, "_": str(time.time_ns())}
            try:
                response = self.client.request(
                    method,
                    f"{self.base_url}/api/{endpoint}",
                    params=query,
                    **kwargs,
                )
            except httpx2.RequestError as exc:
                if attempt + 1 < attempts:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise OmekaError(f"{method} {endpoint}: {type(exc).__name__}") from None
            if not response.is_success:
                raise OmekaError(
                    f"{method} {endpoint}: HTTP {response.status_code}",
                    response.status_code,
                )
            return response
        raise AssertionError("No request attempt")

    def get(self, kind: str, rid: int) -> Record:
        return self.request("GET", f"{kind}/{rid}").json()

    def listing(
        self,
        kind: str,
        *,
        expected_ids: set[int] | None = None,
        per_page: int = 50,
        **filters: Any,
    ) -> list[Record]:
        """Verify each listing against counts and, for media, its parent references."""
        for attempt in range(5):
            records: dict[int, Record] = {}
            totals: set[int] = set()
            page = 1
            while True:
                response = self.request(
                    "GET",
                    kind,
                    params={
                        **filters,
                        "page": page,
                        "per_page": per_page,
                        "sort_by": "id",
                        "sort_order": "asc",
                    },
                )
                total = response.headers.get("omeka-s-total-results")
                if total is not None:
                    try:
                        totals.add(int(total))
                    except ValueError:
                        raise OmekaError(f"Invalid {kind} count header") from None
                batch = response.json()
                if not batch:
                    count_ok = (
                        totals == {len(records)} if totals else expected_ids is not None
                    )
                    if count_ok and (
                        expected_ids is None or records.keys() == expected_ids
                    ):
                        return list(records.values())
                    break
                ids = {record["o:id"] for record in batch}
                if len(ids) != len(batch) or ids.intersection(records):
                    break
                records.update((record["o:id"], record) for record in batch)
                if totals == {len(records)} and (
                    expected_ids is None or records.keys() == expected_ids
                ):
                    return list(records.values())
                page += 1
            if attempt < 4:
                time.sleep(2 * (attempt + 1))
        raise OmekaError(
            f"Incomplete {kind} listing for {filters}: got {len(records)}, "
            f"server counts {sorted(totals)}, referenced count "
            f"{len(expected_ids) if expected_ids is not None else 'unknown'}"
        )

    def find(self, kind: str, identifier: str, property_id: int = 10) -> list[Record]:
        return self.listing(
            kind,
            **{
                "property[0][property]": property_id,
                "property[0][type]": "eq",
                "property[0][text]": identifier,
            },
        )

    def post(
        self,
        kind: str,
        payload: Record,
        file: Path | None = None,
        *,
        filename: str | None = None,
    ) -> Record:
        if file is None:
            return self.request("POST", kind, json=payload).json()
        filename = filename or file.name
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with file.open("rb") as source:
            return self.request(
                "POST",
                kind,
                data={"data": json.dumps(payload, ensure_ascii=False)},
                files={"file[0]": (filename, source, mime)},
            ).json()

    def patch(self, kind: str, rid: int, payload: Record) -> Record:
        return self.request("PATCH", f"{kind}/{rid}", json=payload).json()
