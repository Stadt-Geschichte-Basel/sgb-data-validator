"""fetch_items must return the complete item set or fail (PR #46)."""

import httpx2
import pytest

from sgb_validator import api
from sgb_validator.api import OmekaAPI


def make_validator(passes: list[list[int]], total: int) -> OmekaAPI:
    """Validator whose API returns the given item ids, one list per pass."""
    state = {"pass": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        page = int(request.url.params["page"])
        assert request.url.params["_"], "each request needs a cache-busting nonce"
        ids = passes[min(state["pass"], len(passes) - 1)]
        if page == 1:
            body = [{"o:id": i} for i in ids]
        else:
            body = []
            state["pass"] += 1
        return httpx2.Response(
            200, json=body, headers={"omeka-s-total-results": str(total)}
        )

    return OmekaAPI("https://omeka.example", transport=httpx2.MockTransport(handler))


def test_fetch_items_retries_a_truncated_listing(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(api.time, "sleep", sleeps.append)
    validator = make_validator([[1, 2], [1, 2, 3]], total=3)

    items = validator.listing("items", item_set_id=10780)

    assert sorted(i["o:id"] for i in items) == [1, 2, 3]
    assert sleeps == [2]


def test_fetch_items_fails_when_truncation_persists(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(api.time, "sleep", sleeps.append)
    validator = make_validator([[1, 2]], total=3)

    with pytest.raises(RuntimeError, match="Incomplete items listing"):
        validator.listing("items", item_set_id=10780)

    # No wait after the last attempt.
    assert sleeps == [2, 4, 6, 8]
