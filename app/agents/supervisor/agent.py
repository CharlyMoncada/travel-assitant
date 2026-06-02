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
    supervisor_messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)
    ] + history + [HumanMessage(content=message)]

    # Detailed message telemetry logs
    logger.info("==================================================")
    logger.info("INSPECTING PAYLOAD FOR THE SUPERVISOR LLM")
    logger.info("==================================================")
    for idx, msg in enumerate(supervisor_messages):
        msg_class = msg.__class__.__name__
        msg_type = getattr(msg, "type", None)
        msg_content = str(getattr(msg, "content", ""))
        logger.info(
            "Message [%d] -> Class: %s | Type: %s | Content: '%s...'", 
            idx, msg_class, msg_type, msg_content[:50].replace('\n', ' ')
        )
    logger.info("==================================================")

    logger.info("Invoking the Supervisor LLM to classify/respond to the request")
    supervisor_response = await llm.ainvoke(supervisor_messages)
    supervisor_text = supervisor_response.content.strip()
    logger.info("Supervisor LLM responds: '%s'", supervisor_text)

    route = None
    if "[ROUTE:" in supervisor_text:
        try:
            # Extract content inside [ROUTE: ...] even if there is additional text
            route_part = supervisor_text.split("[ROUTE:")[1].split("]")[0]
            route = route_part.strip().lower()
            # Map common aliases or sub-specialty derivations to the official 'general' specialist
            if route in ["rules", "logistics"]:
                logger.info("Mapping detected alias '%s' by the LLM to the official 'general' route", route)
                route = "general"
        except Exception as e:
            logger.warning("Could not parse route from supervisor response: %s", e)
            
    return route, supervisor_text
