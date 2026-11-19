"""Exercise the Omeka HTTP boundary with an in-process transport."""

import httpx2
import pytest

from sgb_validator.api import OmekaAPI, OmekaError


def test_credentials_and_nonce_go_only_to_the_configured_api(caplog):
    caplog.set_level("INFO", logger="httpx2")

    def handler(request):
        assert request.url.host == "omeka.example"
        assert request.url.path == "/collection/api/items/5"
        assert request.url.params["key_identity"] == "identity"
        assert request.url.params["key_credential"] == "secret+credential"
        assert request.url.params["_"]
        assert request.headers["Cache-Control"] == "no-cache"
        return httpx2.Response(302, headers={"Location": "https://external.example"})

    with OmekaAPI(
        "https://omeka.example/collection/api/",
        "identity",
        "secret+credential",
        transport=httpx2.MockTransport(handler),
    ) as api:
        with pytest.raises(OmekaError, match="GET items/5: HTTP 302") as error:
            api.get("items", 5)
    assert "secret" not in str(error.value)
    assert "secret" not in caplog.text
    assert "key_identity=" not in caplog.text


def test_transport_error_does_not_disclose_credentials(monkeypatch):
    from sgb_validator import api as module

    def handler(request):
        raise httpx2.ConnectError(str(request.url), request=request)

    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    with OmekaAPI(
        "https://omeka.example",
        "identity",
        "secret",
        transport=httpx2.MockTransport(handler),
    ) as api:
        with pytest.raises(OmekaError, match="ConnectError") as error:
            api.get("items", 1)
    assert "secret" not in str(error.value)


def test_https_uses_the_system_trust_store():
    import truststore

    assert isinstance(httpx2.create_ssl_context(trust_env=False), truststore.SSLContext)
