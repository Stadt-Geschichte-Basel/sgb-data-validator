from collections.abc import Iterable

import pytest


INTEGRATION_HINTS: tuple[str, ...] = (
    "integration",
    "offline_workflow",
    "iconclass_integration",
    "creation",
    "api.py",  # broader API tests tend to be integration-ish
)


def _contains_any(text: str, parts: Iterable[str]) -> bool:
    return any(p in text for p in parts)


def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:  # noqa: D401
    """Auto-categorize tests into unit/integration based on file name.

    - Files with common integration hints are marked as `integration`
    - Everything else is marked as `unit`
    """
    for item in items:
        nodeid = item.nodeid.lower()

        if _contains_any(nodeid, INTEGRATION_HINTS):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
