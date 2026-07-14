import logging
from typing import Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable

from ..finance import create_finance_agent
from ..general import create_general_agent
from ..recommender import create_recommender_agent
from ..reminder import create_reminder_agent

logger = logging.getLogger(__name__)


class SubAgentExecutor:
    @staticmethod
    def get_agent_focus_directive(route: str) -> str:
        if route == "finance":
            return (
                "\n\n--- FOCUS INSTRUCTION (NON-NEGOTIABLE) ---\n"
                "You are the Finance specialist in a multi-agent system. The user message may contain tasks for OTHER agents (reminders, packing, travel info). "
                "You MUST silently ignore every non-finance part. "
                "Act ONLY on finance-related actions using your tools. "
                "Do NOT mention, acknowledge, redirect, or comment on any other part of the request. "
                "Do NOT say 'I can only handle finance' or 'for reminders please...' — simply respond as if the user only asked about finances."
            )
        elif route == "reminder":
            return (
                "\n\n--- FOCUS INSTRUCTION (NON-NEGOTIABLE) ---\n"
                "You are the Reminders specialist in a multi-agent system. The user message may contain tasks for OTHER agents (expenses, packing, travel info). "
                "You MUST silently ignore every non-reminder part. "
                "Act ONLY on reminder-related actions using your tools. "
                "Do NOT mention, acknowledge, redirect, or comment on any other part of the request. "
                "Do NOT say 'I can only handle reminders' or 'for expenses please...' — simply respond as if the user only asked about reminders."
            )
        elif route == "recommender":
            return (
                "\n\n--- FOCUS INSTRUCTION (NON-NEGOTIABLE) ---\n"
                "You are the Travel Recommender specialist in a multi-agent system. The user message may contain tasks for OTHER agents (expenses, reminders). "
                "You MUST silently ignore every non-recommender part. "
                "Act ONLY on weather and packing recommendations using your tools. "
                "Do NOT mention, acknowledge, redirect, or comment on any other part of the request. "
                "Simply respond as if the user only asked for travel/packing recommendations."
            )
        elif route == "general":
            return (
                "\n\n--- FOCUS INSTRUCTION (NON-NEGOTIABLE) ---\n"
                "You are the General Travel specialist in a multi-agent system. The user message may contain tasks for OTHER agents (expenses, reminders, packing). "
                "You MUST silently ignore every part outside general conversation, travel documentation, or real-time searches. "
                "Act ONLY on general info/search actions using your tools. "
                "Do NOT mention, acknowledge, redirect, or comment on any other part of the request. "
                "Simply respond as if the user only asked for general travel information."
            )
        return ""

    @classmethod
    @traceable(name="run_specialized_agent")
    async def run_specialized_agent(
        cls,
        llm: ChatOpenAI,
        route: str,
        message: str,
        config: dict,
        langchain_tools_by_server: dict[str, list],
    ) -> tuple[Any, str]:
        if route == "finance":
            finance_tools = []
            for url, tools in langchain_tools_by_server.items():
                if "8002" in url or "finance" in url:
                    finance_tools.extend(tools)
            specialized_agent = create_finance_agent(
                llm,
                finance_tools,
            )

        elif route == "reminder":
            reminder_tools = []
            for url, tools in langchain_tools_by_server.items():
                if "8003" in url or "reminder" in url:
                    reminder_tools.extend(tools)
            specialized_agent = create_reminder_agent(
                llm,
                reminder_tools,
            )

        elif route == "general":
            specialized_agent = create_general_agent(
                llm,
            )

        elif route == "recommender":
            specialized_agent = create_recommender_agent(
                llm,
            )

        else:
            logger.warning("Unknown route '%s', falling back to 'general' agent", route)
            specialized_agent = create_general_agent(
                llm,
            )

        focus_message = message + cls.get_agent_focus_directive(route)

        agent_response = await specialized_agent.ainvoke(
            {
                "messages": [
                    HumanMessage(content=focus_message)
                ]
            },
            config=config,
        )

        messages = agent_response.get("messages", [])
        output = ""

        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                output = msg.content
                break

        if not output and messages:
            output = (
                messages[-1].content
                if hasattr(messages[-1], "content")
                else str(messages[-1])
            )

        elif not output:
            output = agent_response.get("output", str(agent_response))

        return agent_response, output
