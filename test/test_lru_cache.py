"""Test LRU cache functionality for URI checking (Issue #32)"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validate import OmekaValidator


@pytest.mark.asyncio
async def test_uri_cache_hit():
    """Test that cached URIs are returned without making new requests"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)

    # Mock the HTTP request
    with patch("httpx.AsyncClient.head") as mock_head:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"location": None}
        mock_head.return_value = mock_response

        # First call - should make HTTP request
        result1 = await validator.check_single_uri("https://example.com/test1")
        assert result1 == (200, None)
        assert mock_head.call_count == 1

        # Second call - should use cache, no new HTTP request
        result2 = await validator.check_single_uri("https://example.com/test1")
        assert result2 == (200, None)
        assert mock_head.call_count == 1  # Still 1, not 2

        # Verify the URI is in the cache
        assert "https://example.com/test1" in validator.uri_cache


@pytest.mark.asyncio
async def test_uri_cache_miss():
    """Test that different URIs make separate requests"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)

    with patch("httpx.AsyncClient.head") as mock_head:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"location": None}
        mock_head.return_value = mock_response

        # Different URIs should each make a request
        result1 = await validator.check_single_uri("https://example.com/test1")
        assert result1 == (200, None)
        assert mock_head.call_count == 1

        result2 = await validator.check_single_uri("https://example.com/test2")
        assert result2 == (200, None)
        assert mock_head.call_count == 2

        # Both should be in cache
        assert "https://example.com/test1" in validator.uri_cache
        assert "https://example.com/test2" in validator.uri_cache


@pytest.mark.asyncio
async def test_cache_lru_ordering():
    """Test that LRU ordering is maintained (recently used items move to end)"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)

    with patch("httpx.AsyncClient.head") as mock_head:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"location": None}
        mock_head.return_value = mock_response

        # Add three URIs to cache
        await validator.check_single_uri("https://example.com/url1")
        await validator.check_single_uri("https://example.com/url2")
        await validator.check_single_uri("https://example.com/url3")

        # Cache order should be: url1, url2, url3
        cache_keys = list(validator.uri_cache.keys())
        assert cache_keys == [
            "https://example.com/url1",
            "https://example.com/url2",
            "https://example.com/url3",
        ]

        # Access url1 again - it should move to the end
        await validator.check_single_uri("https://example.com/url1")

        # Cache order should now be: url2, url3, url1
        cache_keys = list(validator.uri_cache.keys())
        assert cache_keys == [
            "https://example.com/url2",
            "https://example.com/url3",
            "https://example.com/url1",
        ]


@pytest.mark.asyncio
async def test_cache_eviction():
    """Test that oldest entries are evicted when cache is full"""
    # Create validator with small cache size for testing
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)
    validator.uri_cache_max_size = 3  # Set small cache size for testing

    with patch("httpx.AsyncClient.head") as mock_head:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"location": None}
        mock_head.return_value = mock_response

        # Fill cache to capacity
        await validator.check_single_uri("https://example.com/url1")
        await validator.check_single_uri("https://example.com/url2")
        await validator.check_single_uri("https://example.com/url3")

        assert len(validator.uri_cache) == 3
        assert "https://example.com/url1" in validator.uri_cache

        # Add one more - should evict url1 (oldest)
        await validator.check_single_uri("https://example.com/url4")

        assert len(validator.uri_cache) == 3
        assert "https://example.com/url1" not in validator.uri_cache
        assert "https://example.com/url2" in validator.uri_cache
        assert "https://example.com/url3" in validator.uri_cache
        assert "https://example.com/url4" in validator.uri_cache


@pytest.mark.asyncio
async def test_cache_eviction_with_reuse():
    """Test that recently used entries are not evicted"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)
    validator.uri_cache_max_size = 3

    with patch("httpx.AsyncClient.head") as mock_head:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"location": None}
        mock_head.return_value = mock_response

        # Fill cache
        await validator.check_single_uri("https://example.com/url1")
        await validator.check_single_uri("https://example.com/url2")
        await validator.check_single_uri("https://example.com/url3")

        # Access url1 again - moves it to end
        await validator.check_single_uri("https://example.com/url1")

        # Cache order: url2, url3, url1
        # Add url4 - should evict url2 (oldest)
        await validator.check_single_uri("https://example.com/url4")

        assert len(validator.uri_cache) == 3
        assert "https://example.com/url1" in validator.uri_cache  # Recently used, kept
        assert "https://example.com/url2" not in validator.uri_cache  # Oldest, evicted
        assert "https://example.com/url3" in validator.uri_cache
        assert "https://example.com/url4" in validator.uri_cache


@pytest.mark.asyncio
async def test_cache_stores_error_results():
    """Test that failed requests are also cached"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)

    with patch("httpx.AsyncClient") as mock_client:
        # Create async context manager mock
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        # Simulate an error
        import httpx

        mock_instance.head.side_effect = httpx.RequestError("Connection failed")

        # First call - makes request and caches error
        result1 = await validator.check_single_uri("https://broken.example.com")
        assert result1[0] == -1  # Error status code
        assert "Connection failed" in result1[1]
        assert mock_instance.head.call_count == 1

        # Second call - should return cached error without new request
        result2 = await validator.check_single_uri("https://broken.example.com")
        assert result2[0] == -1
        assert "Connection failed" in result2[1]
        assert mock_instance.head.call_count == 1  # Still 1, no new request

        # Verify the failed URI is in cache
        assert "https://broken.example.com" in validator.uri_cache


@pytest.mark.asyncio
async def test_cache_stores_http_error_codes():
    """Test that HTTP error codes (404, 500, etc.) are cached"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)

    with patch("httpx.AsyncClient.head") as mock_head:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.headers = {"location": None}
        mock_head.return_value = mock_response

        # First call - makes request and caches 404
        result1 = await validator.check_single_uri("https://example.com/notfound")
        assert result1 == (404, None)
        assert mock_head.call_count == 1

        # Second call - should return cached 404
        result2 = await validator.check_single_uri("https://example.com/notfound")
        assert result2 == (404, None)
        assert mock_head.call_count == 1  # No new request

        assert "https://example.com/notfound" in validator.uri_cache


@pytest.mark.asyncio
async def test_cache_max_size_default():
    """Test that the cache has the correct default max size"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)
    assert validator.uri_cache_max_size == 10000


@pytest.mark.asyncio
async def test_cache_stores_redirect_info():
    """Test that redirect information is cached"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)

    with patch("httpx.AsyncClient.head") as mock_head:
        mock_response = AsyncMock()
        mock_response.status_code = 301
        mock_response.headers = {"location": "https://example.com/new-location"}
        mock_head.return_value = mock_response

        # First call - makes request and caches redirect
        result1 = await validator.check_single_uri("https://example.com/old")
        assert result1 == (301, "https://example.com/new-location")
        assert mock_head.call_count == 1

        # Second call - should return cached redirect
        result2 = await validator.check_single_uri("https://example.com/old")
        assert result2 == (301, "https://example.com/new-location")
        assert mock_head.call_count == 1

        assert "https://example.com/old" in validator.uri_cache


def test_cache_initialization():
    """Test that cache is properly initialized"""
    validator = OmekaValidator("https://omeka.unibe.ch", check_uris=True)

    # Cache should be empty initially
    assert len(validator.uri_cache) == 0

    # Cache should be an OrderedDict
    from collections import OrderedDict

    assert isinstance(validator.uri_cache, OrderedDict)

    # Cache max size should be set
    assert validator.uri_cache_max_size == 10000


if __name__ == "__main__":
    print("Running LRU cache tests...")

    # Run tests that don't require pytest
    print("✓ Test: cache_initialization")
    test_cache_initialization()

    print("\n✅ Basic cache tests passed!")
    print("\nRun 'pytest test/test_lru_cache.py' to run all async tests.")
