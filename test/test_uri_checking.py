"""Exercise opt-in link checks with a separate HTTPX2 client."""

import asyncio

import httpx2
import pytest

from sgb_validator.links import LinkChecker, extract_uris_from_data
from sgb_validator.validation import Findings


def test_extract_uris():
    assert extract_uris_from_data(
        {
            "dcterms:source": [{"@id": "https://example.org/source"}],
            "dcterms:title": [{"@value": "Title"}],
            "o:original_url": "https://example.org/file.jpg",
        }
    ) == [
        ("dcterms:source[0].@id", "https://example.org/source"),
        ("o:original_url", "https://example.org/file.jpg"),
    ]


@pytest.mark.parametrize(
    "status,severity,errors",
    [(404, "warning", 1), (503, "warning", 0), (503, "error", 1)],
)
def test_link_failure_severity_and_head_fallback(status, severity, errors):
    requests = []

    def handler(request):
        requests.append(request.method)
        assert not request.url.params
        assert "Authorization" not in request.headers
        return httpx2.Response(405 if request.method == "HEAD" else status)

    findings = Findings()

    async def check():
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(handler)
        ) as client:
            checker = LinkChecker(client, findings, severity=severity)
            await checker.check_uri_async(
                "https://example.org/file", "Item", 1, "source"
            )
            await checker.check_uri_async(
                "https://example.org/file", "Item", 2, "source"
            )

    asyncio.run(check())
    assert requests == ["HEAD", "GET"]
    assert findings.failed_uris == 2
    assert len(findings.errors) == 2 * errors
    assert len(findings.warnings) == 2 * (1 - errors)


def test_external_redirect_warning_without_following():
    def handler(request):
        assert request.url.host == "example.org"
        return httpx2.Response(302, headers={"Location": "https://redirect.example"})

    findings = Findings()

    async def check():
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(handler)
        ) as client:
            checker = LinkChecker(client, findings, check_redirects=True)
            await checker.check_uri_async(
                "https://example.org/file", "Item", 1, "source"
            )

    asyncio.run(check())
    assert "different domain" in findings.warnings[0].message
