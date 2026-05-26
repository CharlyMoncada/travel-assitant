from langchain.agents import create_agent
from .prompts import REMINDER_AGENT_SYSTEM_PROMPT

def create_reminder_agent(llm, tools: list, checkpointer):
    """
    Creates and compiles the sub-agent specialized in Reminders and Tasks.
    """
    # Filter only reminder tools
    reminder_tools = [t for t in tools if "reminder" in t.name]
    return create_agent(
        llm,
        reminder_tools,
        system_prompt=REMINDER_AGENT_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        debug=False,
    )
