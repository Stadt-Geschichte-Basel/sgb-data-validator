"""fetch_items must return the complete item set or fail (PR #46)."""

import httpx
import pytest

import validate
from validate import OmekaValidator


def make_validator(passes: list[list[int]], total: int) -> OmekaValidator:
    """Validator whose API returns the given item ids, one list per pass."""
    state = {"pass": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        assert request.url.params["_"], "each request needs a cache-busting nonce"
        ids = passes[min(state["pass"], len(passes) - 1)]
        if page == 1:
            body = [{"o:id": i} for i in ids]
        else:
            body = []
            state["pass"] += 1
        return httpx.Response(
            200, json=body, headers={"omeka-s-total-results": str(total)}
        )

    validator = OmekaValidator("https://omeka.example")
    validator.client = httpx.Client(transport=httpx.MockTransport(handler))
    return validator


def test_fetch_items_retries_a_truncated_listing(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(validate.time, "sleep", sleeps.append)
    validator = make_validator([[1, 2], [1, 2, 3]], total=3)

    items = validator.fetch_items(10780)

    assert sorted(i["o:id"] for i in items) == [1, 2, 3]
    assert sleeps == [2]


def test_fetch_items_fails_when_truncation_persists(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(validate.time, "sleep", sleeps.append)
    validator = make_validator([[1, 2]], total=3)

    with pytest.raises(RuntimeError, match="fetched 2 of 3 items after 5 attempts"):
        validator.fetch_items(10780)

    # No wait after the last attempt.
    assert sleeps == [2, 4, 6, 8]
