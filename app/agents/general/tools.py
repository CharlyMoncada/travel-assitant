import json
import logging
from pydantic import BaseModel

from langchain_core.tools import StructuredTool

from app.services.rag import query_normative_documents
from app.services.brave_search import (
    brave_web_search,
    format_search_results_for_llm,
    is_brave_available,
)

logger = logging.getLogger(__name__)


class RulesSchema(BaseModel):
    text: str


class TravelSearchSchema(BaseModel):
    text: str


def make_rules_coroutine():
    async def call_rules(text: str) -> str:
        try:
            answer, sources = query_normative_documents(text)
            payload = {"query": text, "answer": answer, "sources": sources}
            return json.dumps(payload, ensure_ascii=False)
        except Exception as e:
            logger.exception("Error executing rules tool")
            return json.dumps({"error": str(e)})

    return call_rules


def make_travel_search_coroutine():
    async def call_travel_search(text: str) -> str:
        """Search for flights, hotels, transport and travel options using Brave Search."""
        if not is_brave_available():
            logger.warning(
                "travel_search tool called but BRAVE_API_KEY is not configured"
            )
            return json.dumps(
                {
                    "query": text,
                    "results": [],
                    "warning": (
                        "Live search is not available because BRAVE_API_KEY "
                        "is not configured. Please add it to the .env file "
                        "to enable real-time flight, hotel and transport search."
                    ),
                },
                ensure_ascii=False,
            )

        # Use the user text directly — it's already descriptive enough for travel queries.
        # For very short inputs (< 4 words) we append a travel context hint.
        words = text.split()
        search_query = text if len(words) >= 4 else f"{text} travel"
        logger.info("travel_search tool: searching Brave for %r", search_query)

        try:
            result = await brave_web_search(search_query, count=5)
            return format_search_results_for_llm(result)
        except Exception as e:
            logger.exception("Error executing travel_search tool")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    return call_travel_search


def get_general_tools() -> list:
    return [
        StructuredTool(
            name="rules",
            description=(
                "MANDATORY tool for answering travel regulation questions. "
                "Use this for visas, entry requirements, passports, travel documents, COVID rules, "
                "vaccines, safety advice, country requirements and any normative travel information. "
                "The final answer must be grounded only on the retrieved RAG documents."
            ),
            coroutine=make_rules_coroutine(),
            func=lambda **kwargs: "",
            args_schema=RulesSchema,
        ),
        StructuredTool(
            name="travel_search",
            description=(
                "Real-time web search tool for travel planning questions. "
                "Use this strictly for searching information about flights, hotels, transport options, travel routes, prices, "
                "schedules, availability, or any practical travel planning. "
                "This is a search-only tool and CANNOT reserve, book, purchase, or register flights, hotels, or tickets. "
                "Do NOT use this for travel regulations, visas, or entry requirements — use 'rules' instead."
            ),
            coroutine=make_travel_search_coroutine(),
            func=lambda **kwargs: "",
            args_schema=TravelSearchSchema,
        ),
    ]

