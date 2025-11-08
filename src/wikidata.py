"""Wikidata integration utilities.

This module provides functions to interact with the Wikidata API,
including searching for entities and resolving identifiers.
"""

import asyncio
from typing import Any

import httpx


async def search_wikidata_entity(
    query: str,
    language: str = "de",
    limit: int = 5,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Search for Wikidata entities using the Wikidata Search API.

    Args:
        query: Search query (name, label, or description)
        language: Language code for search (default: "de" for German)
        limit: Maximum number of results to return (default: 5)
        timeout: Request timeout in seconds (default: 10.0)

    Returns:
        List of search results, each containing:
        - id: Wikidata QID (e.g., "Q123")
        - label: Entity label in the specified language
        - description: Entity description in the specified language
        - url: Full URL to the Wikidata entity

    Example:
        >>> results = await search_wikidata_entity("Basel")
        >>> for result in results:
        ...     print(f"{result['id']}: {result['label']} - {result['description']}")
        Q78: Basel - Stadt in der Schweiz
    """
    if not query:
        return []

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": language,
        "limit": limit,
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("search", []):
                results.append(
                    {
                        "id": item.get("id", ""),
                        "label": item.get("label", ""),
                        "description": item.get("description", ""),
                        "url": f"https://www.wikidata.org/wiki/{item.get('id', '')}",
                    }
                )

            return results

        except httpx.HTTPError as e:
            print(f"Error searching Wikidata: {e}")
            return []


def search_wikidata_entity_sync(
    query: str,
    language: str = "de",
    limit: int = 5,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Synchronous wrapper for search_wikidata_entity.

    Args:
        query: Search query (name, label, or description)
        language: Language code for search (default: "de" for German)
        limit: Maximum number of results to return (default: 5)
        timeout: Request timeout in seconds (default: 10.0)

    Returns:
        List of search results (see search_wikidata_entity for details)

    Example:
        >>> results = search_wikidata_entity_sync("Basel")
        >>> print(f"Found {len(results)} results")
    """
    return asyncio.run(
        search_wikidata_entity(query, language=language, limit=limit, timeout=timeout)
    )


async def search_multiple_entities(
    queries: list[str],
    language: str = "de",
    limit: int = 5,
    timeout: float = 10.0,
) -> dict[str, list[dict[str, Any]]]:
    """Search for multiple Wikidata entities concurrently.

    Args:
        queries: List of search queries
        language: Language code for search (default: "de" for German)
        limit: Maximum number of results per query (default: 5)
        timeout: Request timeout in seconds (default: 10.0)

    Returns:
        Dictionary mapping each query to its search results

    Example:
        >>> queries = ["Basel", "Zürich", "Bern"]
        >>> results = await search_multiple_entities(queries)
        >>> for query, matches in results.items():
        ...     print(f"{query}: {len(matches)} matches")
    """
    if not queries:
        return {}

    tasks = [
        search_wikidata_entity(query, language=language, limit=limit, timeout=timeout)
        for query in queries
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Map queries to results, handling exceptions
    result_dict = {}
    for query, result in zip(queries, results, strict=True):
        if isinstance(result, Exception):
            print(f"Error searching for '{query}': {result}")
            result_dict[query] = []
        else:
            result_dict[query] = result

    return result_dict


def search_multiple_entities_sync(
    queries: list[str],
    language: str = "de",
    limit: int = 5,
    timeout: float = 10.0,
) -> dict[str, list[dict[str, Any]]]:
    """Synchronous wrapper for search_multiple_entities.

    Args:
        queries: List of search queries
        language: Language code for search (default: "de" for German)
        limit: Maximum number of results per query (default: 5)
        timeout: Request timeout in seconds (default: 10.0)

    Returns:
        Dictionary mapping each query to its search results

    Example:
        >>> queries = ["Basel", "Zürich", "Bern"]
        >>> results = search_multiple_entities_sync(queries)
    """
    return asyncio.run(
        search_multiple_entities(
            queries, language=language, limit=limit, timeout=timeout
        )
    )
