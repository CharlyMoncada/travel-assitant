"""
Brave Search API client for the Travel Assistant.

Provides async travel-focused search using the Brave Search REST API.
No MCP server is launched — this calls the HTTP endpoint directly,
which is simpler and more reliable inside an existing async application.

Configuration:
    Set BRAVE_API_KEY in the project .env file.
    Optionally set BRAVE_SEARCH_COUNT (default: 5, max: 20).

API docs: https://api.search.brave.com/app/documentation/web-search/get-started
"""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_RESULT_COUNT = int(os.getenv("BRAVE_SEARCH_COUNT", "5"))
_REQUEST_TIMEOUT_S = 10


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_brave_api_key() -> Optional[str]:
    """Return the Brave Search API key from the environment, or None."""
    return os.getenv("BRAVE_API_KEY") or None


def is_brave_available() -> bool:
    """Return True if a Brave API key is configured."""
    return bool(get_brave_api_key())


async def brave_web_search(
    query: str,
    *,
    count: int = _DEFAULT_RESULT_COUNT,
    country: str = "ES",
    search_lang: str = "es",
) -> dict:
    """
    Perform a Brave web search and return structured results.

    Args:
        query:       The search query string.
        count:       Number of results to return (1-20).
        country:     Two-letter country code to bias results (default: "ES").
        search_lang: Language code for search results (default: "es").

    Returns:
        A dict with keys:
          - "query"   (str)  -- the original query
          - "results" (list) -- list of {title, url, description} dicts
          - "total"   (int)  -- number of results returned
        On error, returns {"query": query, "results": [], "error": "<message>"}
    """
    api_key = get_brave_api_key()
    if not api_key:
        logger.warning("Brave Search: BRAVE_API_KEY not configured")
        return {
            "query": query,
            "results": [],
            "error": "BRAVE_API_KEY is not configured. Add it to the .env file.",
        }

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": min(max(1, count), 20),
        "country": country,
        "search_lang": search_lang,
        "result_filter": "web",
    }

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_S) as client:
            response = await client.get(
                _BRAVE_SEARCH_URL, headers=headers, params=params
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        logger.warning("Brave Search: request timed out for query %r", query)
        return {"query": query, "results": [], "error": "Search request timed out."}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Brave Search: HTTP %s for query %r: %s",
            exc.response.status_code,
            query,
            exc.response.text[:200],
        )
        return {
            "query": query,
            "results": [],
            "error": f"Brave Search returned HTTP {exc.response.status_code}.",
        }
    except Exception as exc:
        logger.exception("Brave Search: unexpected error for query %r", query)
        return {"query": query, "results": [], "error": str(exc)}

    # Parse web results
    raw_results = (data.get("web") or {}).get("results") or []
    results = [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
        }
        for item in raw_results
    ]

    logger.info(
        "Brave Search: query=%r returned %d results", query, len(results)
    )
    return {"query": query, "results": results, "total": len(results)}


def format_search_results_for_llm(search_response: dict) -> str:
    """
    Format a brave_web_search response dict into a JSON string
    suitable for returning from a LangChain tool.
    """
    return json.dumps(search_response, ensure_ascii=False, indent=2)
