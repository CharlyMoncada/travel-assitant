import json
import logging
from pydantic import BaseModel

from langchain_core.tools import StructuredTool

from app.services.rag import query_normative_documents

logger = logging.getLogger(__name__)


class RulesSchema(BaseModel):
    text: str


class LogisticsSchema(BaseModel):
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


def make_logistics_coroutine():
    async def call_logistics(text: str) -> str:
        return json.dumps(
            {
                "message": "TO DO: This 'logistics' tool is a placeholder. Internet-connected flight/hotel search will be implemented in the next iteration.",
                "query": text,
            },
            ensure_ascii=False,
        )

    return call_logistics


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
            name="logistics",
            description="TO DO: Internet-connected flight/hotel search. Currently works as a local placeholder.",
            coroutine=make_logistics_coroutine(),
            func=lambda **kwargs: "",
            args_schema=LogisticsSchema,
        ),
    ]
