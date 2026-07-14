import logging
from typing import Optional
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage

from .prompts import SUPERVISOR_SYSTEM_PROMPT, MEMORY_RULE

logger = logging.getLogger(__name__)


class RoutingDecision(BaseModel):
    routes: list[str] = Field(
        default_factory=list,
        description="The target sub-agent routes to trigger in order: 'finance', 'reminder', 'general', 'recommender'. Leave empty if direct response/interaction."
    )
    response: Optional[str] = Field(
        None,
        description="The direct text response to the user for smalltalk, clarifications, greetings, or out-of-scope rejections. Leave empty if routing."
    )


async def run_supervisor(llm, history: list, message: str) -> tuple[list[str], str]:
    """
    Invokes the Supervisor LLM with structured outputs to determine routing or direct conversation.
    Returns a tuple (routes, response_text).
    """

    supervisor_messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT + "\n\n" + MEMORY_RULE)
    ] + history + [HumanMessage(content=message)]

    logger.info("==================================================")
    logger.info("INSPECTING PAYLOAD FOR THE SUPERVISOR LLM")
    logger.info("==================================================")

    for idx, msg in enumerate(supervisor_messages):
        msg_class = msg.__class__.__name__
        msg_type = getattr(msg, "type", None)
        msg_content = str(getattr(msg, "content", ""))
        logger.info(
            "Message [%d] -> Class: %s | Type: %s | Content: '%s...'",
            idx,
            msg_class,
            msg_type,
            msg_content[:50].replace("\n", " "),
        )

    logger.info("==================================================")
    logger.info("Invoking the Supervisor LLM with Structured Output (RoutingDecision)")

    try:
        structured_llm = llm.with_structured_output(RoutingDecision)
        supervisor_response = await structured_llm.ainvoke(supervisor_messages)
    except Exception as e:
        logger.error("Error invoking Supervisor with structured outputs: %s", e, exc_info=True)
        # Safe fallback: treat as empty routing decision to default to supervisor chat or general
        supervisor_response = RoutingDecision(routes=[], response="Internal classification error. / Error interno de clasificación.")

    routes = []
    supervisor_text = ""

    if supervisor_response:
        raw_routes = supervisor_response.routes or []
        supervisor_text = supervisor_response.response or ""

        for r in raw_routes:
            if isinstance(r, str):
                r = r.lower().strip()
                if r in ["", "none", "null"]:
                    continue
                if r in ["rules", "logistics", "travel_search"]:
                    logger.info(
                        "Mapping detected alias '%s' by the LLM to the official 'general' route",
                        r,
                    )
                    r = "general"
                if r not in routes:
                    routes.append(r)

    logger.info("Supervisor LLM responds - Routes: %s | Response: '%s'", routes, supervisor_text)

    return routes, supervisor_text