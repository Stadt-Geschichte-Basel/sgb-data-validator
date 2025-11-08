"""Tests for Wikidata integration utilities."""

from src.wikidata import (
    search_multiple_entities_sync,
    search_wikidata_entity_sync,
)


def test_search_wikidata_entity_sync() -> None:
    """Test synchronous Wikidata search."""
    print("\nTest 1: Search for Wikidata entity")
    print("=" * 60)

    # Search for a well-known entity
    results = search_wikidata_entity_sync("Basel", language="de", limit=3)

    assert isinstance(results, list), "Results should be a list"
    assert len(results) > 0, "Should find at least one result for Basel"

    # Check structure of first result
    first_result = results[0]
    assert "id" in first_result, "Result should have 'id' field"
    assert "label" in first_result, "Result should have 'label' field"
    assert "description" in first_result, "Result should have 'description' field"
    assert "url" in first_result, "Result should have 'url' field"

    # Check QID format
    assert first_result["id"].startswith("Q"), "QID should start with 'Q'"
    assert first_result["id"][1:].isdigit(), "QID should be Q followed by digits"

    # Check URL format
    expected_url = f"https://www.wikidata.org/wiki/{first_result['id']}"
    assert first_result["url"] == expected_url, (
        f"URL should be {expected_url}, got {first_result['url']}"
    )

    print(f"  ✓ Found {len(results)} results for 'Basel'")
    print(f"  ✓ First result: {first_result['id']} - {first_result['label']}")
    print(f"  ✓ URL: {first_result['url']}")


def test_search_empty_query() -> None:
    """Test search with empty query."""
    print("\nTest 2: Search with empty query")
    print("=" * 60)

    results = search_wikidata_entity_sync("", language="de", limit=3)

    assert isinstance(results, list), "Results should be a list"
    assert len(results) == 0, "Empty query should return no results"

    print("  ✓ Empty query returns no results")


def test_search_multiple_entities_sync() -> None:
    """Test synchronous search for multiple entities."""
    print("\nTest 3: Search for multiple entities")
    print("=" * 60)

    queries = ["Basel", "Zürich", "Bern"]
    results = search_multiple_entities_sync(queries, language="de", limit=2)

    assert isinstance(results, dict), "Results should be a dictionary"
    assert len(results) == len(queries), "Should have results for all queries"

    for query in queries:
        assert query in results, f"Results should contain '{query}'"
        assert isinstance(results[query], list), (
            f"Results for '{query}' should be a list"
        )
        assert len(results[query]) > 0, f"Should find results for '{query}'"

        # Check first result for each query
        first_result = results[query][0]
        assert first_result["id"].startswith("Q"), "QID should start with 'Q'"

    print(f"  ✓ Searched for {len(queries)} entities")
    for query, matches in results.items():
        if matches:
            first = matches[0]
            print(f"  ✓ {query}: {first['id']} - {first['label']}")


def test_search_with_language() -> None:
    """Test search with different languages."""
    print("\nTest 4: Search with different languages")
    print("=" * 60)

    # Search in German
    results_de = search_wikidata_entity_sync("Basel", language="de", limit=1)
    # Search in English
    results_en = search_wikidata_entity_sync("Basel", language="en", limit=1)

    assert len(results_de) > 0, "Should find results in German"
    assert len(results_en) > 0, "Should find results in English"

    # Both should find the same entity (Q78 for Basel)
    assert results_de[0]["id"] == results_en[0]["id"], (
        "Same entity should be found in both languages"
    )

    print(f"  ✓ German: {results_de[0]['id']} - {results_de[0]['label']}")
    print(f"  ✓ English: {results_en[0]['id']} - {results_en[0]['label']}")


def test_search_limit() -> None:
    """Test search result limit."""
    print("\nTest 5: Search result limit")
    print("=" * 60)

    # Search with limit 1
    results_1 = search_wikidata_entity_sync("Stadt", language="de", limit=1)
    # Search with limit 5
    results_5 = search_wikidata_entity_sync("Stadt", language="de", limit=5)

    assert len(results_1) <= 1, "Should return at most 1 result"
    assert len(results_5) <= 5, "Should return at most 5 results"
    assert len(results_5) >= len(results_1), "More results with higher limit"

    print(f"  ✓ Limit 1: {len(results_1)} results")
    print(f"  ✓ Limit 5: {len(results_5)} results")


if __name__ == "__main__":
    print("Testing Wikidata integration utilities")
    print("=" * 60)
    print("Note: These tests require internet connectivity to reach Wikidata API")
    print()

    test_search_wikidata_entity_sync()
    test_search_empty_query()
    test_search_multiple_entities_sync()
    test_search_with_language()
    test_search_limit()

    print("\n" + "=" * 60)
    print("✓ All Wikidata tests passed!")
