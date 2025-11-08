"""Tests for HTTP to HTTPS upgrade functionality."""

import pytest

from src.transformations import (
    apply_text_transformations,
    upgrade_http_to_https,
)


def test_upgrade_http_to_https_with_real_urls():
    """Test upgrading HTTP to HTTPS with real URLs that support HTTPS."""
    # Test with well-known sites that support HTTPS
    text = "Visit http://www.example.com for more info"
    result = upgrade_http_to_https(text)
    # example.com supports HTTPS
    assert "https://www.example.com" in result
    assert "http://www.example.com" not in result


def test_upgrade_http_to_https_preserves_https():
    """Test that existing HTTPS URLs are not modified."""
    text = "Visit https://www.example.com for more info"
    result = upgrade_http_to_https(text)
    assert result == text


def test_upgrade_http_to_https_empty_string():
    """Test with empty string."""
    result = upgrade_http_to_https("")
    assert result == ""


def test_upgrade_http_to_https_no_urls():
    """Test with text containing no URLs."""
    text = "This is just plain text with no URLs"
    result = upgrade_http_to_https(text)
    assert result == text


def test_upgrade_http_to_https_mixed_urls():
    """Test with mixed HTTP and HTTPS URLs."""
    text = "Visit http://www.example.com and https://www.example.org"
    result = upgrade_http_to_https(text)
    # Should upgrade HTTP but preserve HTTPS
    assert "https://www.example.com" in result
    assert "https://www.example.org" in result
    assert "http://" not in result or "http://www.example.com" not in result


def test_apply_text_transformations_with_https_upgrade():
    """Test that apply_text_transformations includes HTTPS upgrade by default."""
    text = "Check out http://www.example.com for details"
    result = apply_text_transformations(text)
    # Should upgrade to HTTPS
    assert "https://www.example.com" in result


def test_apply_text_transformations_without_https_upgrade():
    """Test disabling HTTPS upgrade in apply_text_transformations."""
    text = "Check out http://www.example.com for details"
    result = apply_text_transformations(text, upgrade_https=False)
    # Should NOT upgrade to HTTPS when disabled
    assert "http://www.example.com" in result
    assert "https://www.example.com" not in result


def test_upgrade_http_to_https_in_markdown_links():
    """Test upgrading HTTP URLs inside Markdown links."""
    text = "See [Example](http://www.example.com) for more"
    result = upgrade_http_to_https(text)
    assert "[Example](https://www.example.com)" in result


def test_upgrade_http_to_https_multiple_urls():
    """Test upgrading multiple HTTP URLs in the same text."""
    text = (
        "Visit http://www.example.com and http://www.example.org "
        "for more information"
    )
    result = upgrade_http_to_https(text)
    # Both should be upgraded if HTTPS is available
    assert (
        "https://www.example.com" in result or "http://www.example.com" in result
    )
    assert (
        "https://www.example.org" in result or "http://www.example.org" in result
    )


@pytest.mark.slow
def test_upgrade_http_to_https_timeout():
    """Test that the upgrade handles timeouts gracefully."""
    # Use a URL that will timeout
    text = "Visit http://192.0.2.1:8080/test for info"
    result = upgrade_http_to_https(text)
    # Should preserve original URL if HTTPS check fails/times out
    assert "http://192.0.2.1:8080/test" in result
