"""Item listings must return the complete item set or fail (PR #46)."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from omeka_s_client import (
    IncompleteListingError,
    SnapshotConsistencyError,
    TransportResponse,
)

from sgb_validator.api import Omeka
from sgb_validator.snapshots import capture_snapshot


def page(ids, total):
    body = json.dumps([{"o:id": rid} for rid in ids]).encode()
    return TransportResponse(200, {"Omeka-S-Total-Results": str(total)}, body)


def make_client(passes: list[list[int]], total: int) -> Omeka:
    """Return a client whose API returns the given item IDs, one list per pass."""
    state = {"pass": 0}

    def transport(request):
        query = parse_qs(urlsplit(request.url).query)
        ids = passes[min(state["pass"], len(passes) - 1)]
        if query["page"] == ["1"]:
            return page(ids, total)
        state["pass"] += 1
        return page([], total)

    return Omeka("https://omeka.example", transport=transport, sleep=lambda _: None)


def test_listing_retries_a_truncated_listing() -> None:
    with make_client([[1, 2], [1, 2, 3]], total=3) as client:
        items = client.list("items", filters={"item_set_id": 10780}, verify=True)
    assert sorted(i["o:id"] for i in items) == [1, 2, 3]


def test_listing_fails_when_truncation_persists() -> None:
    with make_client([[1, 2]], total=3) as client:
        with pytest.raises(IncompleteListingError, match="three attempts"):
            client.list("items", filters={"item_set_id": 10780}, verify=True)


def test_verified_listing_requires_a_count_header():
    def transport(request):
        return TransportResponse(200, content=b"[]")

    with Omeka("https://omeka.example", transport=transport) as client:
        with pytest.raises(IncompleteListingError, match="No count"):
            client.list("items", verify=True)


def test_snapshot_item_listing_rejects_a_different_membership_with_the_same_count():
    def transport(request):
        url = urlsplit(request.url)
        query = parse_qs(url.query)
        if url.path == "/api/item_sets/1":
            return TransportResponse(200, content=b'{"o:id": 1}')
        descending = query.get("sort_order") == ["desc"]
        ids = [5, 4, 3, 2] if descending else [1, 2, 4, 5]
        return page(ids if query["page"] == ["1"] else [], 4)

    with Omeka("https://omeka.example", transport=transport) as client:
        with pytest.raises(SnapshotConsistencyError, match=r"Missing examples: \[1\]"):
            capture_snapshot(client, 1)
