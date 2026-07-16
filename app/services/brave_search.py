"""
Cliente de la API de Brave Search para el Asistente de Viaje.

Proporciona búsquedas asíncronas enfocadas en viajes usando la API REST de Brave Search.
No se lanza ningún servidor MCP — llama directamente al endpoint HTTP,
lo que es más sencillo y fiable dentro de una aplicación asíncrona existente.

Configuración:
    Establecer BRAVE_API_KEY en el archivo .env del proyecto.
    Opcionalmente establecer BRAVE_SEARCH_COUNT (por defecto: 5, máximo: 20).

Documentación de la API: https://api.search.brave.com/app/documentation/web-search/get-started
"""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_RESULT_COUNT = int(os.getenv("BRAVE_SEARCH_COUNT", "5"))
_REQUEST_TIMEOUT_S = 10


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def get_brave_api_key() -> Optional[str]:
    """Retorna la clave de API de Brave Search desde el entorno, o None."""
    return os.getenv("BRAVE_API_KEY") or None


def is_brave_available() -> bool:
    """Retorna True si hay una clave de API de Brave configurada."""
    return bool(get_brave_api_key())


async def brave_web_search(
    query: str,
    *,
    count: int = _DEFAULT_RESULT_COUNT,
    country: str = "ES",
    search_lang: str = "es",
) -> dict:
    """
    Realiza una búsqueda web en Brave y retorna resultados estructurados.

    Args:
        query:       La cadena de consulta de búsqueda.
        count:       Número de resultados a retornar (1-20).
        country:     Código de país de dos letras para sesgar resultados (por defecto: "ES").
        search_lang: Código de idioma para los resultados de búsqueda (por defecto: "es").

    Returns:
        Un dict con claves:
          - "query"   (str)  -- la consulta original
          - "results" (list) -- lista de dicts {title, url, description}
          - "total"   (int)  -- número de resultados retornados
        En caso de error, retorna {"query": query, "results": [], "error": "<mensaje>"}
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

    # Parsear resultados web
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
    Formatea un dict de respuesta de brave_web_search en una cadena JSON
    adecuada para retornar desde una herramienta LangChain.
    """
    return json.dumps(search_response, ensure_ascii=False, indent=2)
