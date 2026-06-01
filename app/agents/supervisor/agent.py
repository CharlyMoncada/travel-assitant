from typing import Optional
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from .prompts import SUPERVISOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def run_supervisor(llm, history: list, message: str) -> tuple[Optional[str], str]:
    """
    Invokes the Supervisor LLM with the routing skill to determine routing or direct conversation.
    Returns a tuple (route, response_text).
    """

    memory_rule = """
IMPORTANT MEMORY RULE:
If the user asks about something they previously told you, their preferences,
saved context, memory, or personal travel preferences, answer directly using
the conversation history.

Do not route to any specialized agent if the answer is already present in history.

Examples:
- "What is my favorite airport?"
- "What did I tell you before?"
- "Do you remember my travel preference?"
- "Cuál es mi aeropuerto favorito?"
- "Cual es mi aeropuerto favorito para viajar?"

If the answer is present in the conversation history, respond directly.
Do not output [ROUTE: general], [ROUTE: finance] or [ROUTE: reminder].
"""

    supervisor_messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT + "\n\n" + memory_rule)
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
    logger.info("Invoking the Supervisor LLM to classify/respond to the request")

    supervisor_response = await llm.ainvoke(supervisor_messages)
    supervisor_text = supervisor_response.content.strip()

    logger.info("Supervisor LLM responds: '%s'", supervisor_text)

    route = None

    if "[ROUTE:" in supervisor_text:
        try:
            route_part = supervisor_text.split("[ROUTE:")[1].split("]")[0]
            route = route_part.strip().lower()

            if route in ["rules", "logistics"]:
                logger.info(
                    "Mapping detected alias '%s' by the LLM to the official 'general' route",
                    route,
                )
                route = "general"

        except Exception as e:
            logger.warning("Could not parse route from supervisor response: %s", e)

    return route, supervisor_text