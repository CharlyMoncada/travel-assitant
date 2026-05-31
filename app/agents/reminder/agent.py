from langchain.agents import create_agent
from .prompts import get_reminder_system_prompt

def create_reminder_agent(llm, tools: list, checkpointer):
    """
    Creates and compiles the sub-agent specialized in Reminders and Tasks.
    The system prompt is generated at call time to inject the current datetime,
    enabling accurate resolution of relative date expressions (e.g. 'mañana', 'in 3 days').
    """
    reminder_tools = [t for t in tools if "reminder" in t.name]
    return create_agent(
        llm,
        reminder_tools,
        system_prompt=get_reminder_system_prompt(),
        checkpointer=checkpointer,
        debug=False,
    )
