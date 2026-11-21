"""Exercise the Omeka HTTP boundary with an in-process transport."""

import ssl
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from omeka_s_client import (
    ConnectFailed,
    OmekaConnectionError,
    TransportResponse,
    UnsafeRedirectError,
)

from sgb_validator.api import Omeka, OmekaError, find, optional_get


def test_credentials_go_only_to_the_configured_api(caplog):
    caplog.set_level("INFO", logger="httpx2")
    requests = []

    def transport(request):
        requests.append(request)
        url = urlsplit(request.url)
        assert url.netloc == "omeka.example"
        assert url.path == "/collection/api/items/5"
        query = parse_qs(url.query)
        assert query["key_identity"] == ["identity"]
        assert query["key_credential"] == ["secret+credential"]
        assert request.headers["cache-control"] == "no-cache"
        return TransportResponse(302, {"Location": "https://external.example"})

    with Omeka(
        "https://omeka.example/collection/api/",
        "identity",
        "secret+credential",
        transport=transport,
    ) as api:
        with pytest.raises(UnsafeRedirectError) as error:
            api.get("items", 5)
    assert len(requests) == 1
    assert "secret" not in str(error.value)
    assert "secret" not in caplog.text


def test_transport_error_does_not_disclose_credentials():
    def transport(request):
        raise ConnectFailed(request.url)

    with Omeka(
        "https://omeka.example",
        "identity",
        "secret",
        transport=transport,
        sleep=lambda _: None,
    ) as api:
        with pytest.raises(OmekaConnectionError) as error:
            api.get("items", 1)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    ("identity", "credential", "authenticated"),
    [(None, None, False), ("", "", False), ("identity", "secret", True)],
)
def test_unset_keys_open_a_public_client(identity, credential, authenticated):
    with Omeka("https://omeka.example", identity, credential) as api:
        assert api.authenticated is authenticated


def test_partial_keys_are_rejected():
    with pytest.raises(ValueError, match="both Omeka keys"):
        Omeka("https://omeka.example", "identity", "")


def test_find_matches_the_identifier_term():
    requests = []

    def transport(request):
        requests.append(request)
        return TransportResponse(200, {"Omeka-S-Total-Results": "1"}, b'[{"o:id": 7}]')

    with Omeka("https://omeka.example", transport=transport) as api:
        assert find(api, "items", "abb10039") == [{"o:id": 7}]
    query = parse_qs(urlsplit(requests[0].url).query)
    assert query["property[0][property]"] == ["dcterms:identifier"]
    assert query["property[0][type]"] == ["eq"]
    assert query["property[0][text]"] == ["abb10039"]


def test_optional_get_returns_none_only_for_missing_records():
    statuses = iter([404, 500])

    def transport(request):
        return TransportResponse(next(statuses), content=b"{}")

    with Omeka("https://omeka.example", transport=transport, max_retries=0) as api:
        assert optional_get(api, "items", 1) is None
        with pytest.raises(OmekaError) as error:
            optional_get(api, "items", 1)
    assert error.value.status == 500


def test_https_uses_the_system_trust_store():
    context = httpx2.create_ssl_context(trust_env=False)
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED

    if sys.platform in {"darwin", "win32"}:
        import truststore

        assert isinstance(context, truststore.SSLContext)
    else:
        # Linux loads system roots with OpenSSL instead of the truststore wrapper.
        cafile = ssl.get_default_verify_paths().openssl_cafile
        if Path(cafile).is_file():
            system = ssl.create_default_context(cafile=cafile)
            assert set(system.get_ca_certs(binary_form=True)) <= set(
                context.get_ca_certs(binary_form=True)
            )
