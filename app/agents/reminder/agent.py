from langchain.agents import create_agent
from .prompts import get_reminder_system_prompt

def create_reminder_agent(llm, tools: list):
    """
    Creates and compiles the sub-agent specialized in Reminders and Tasks.
    The system prompt is generated at call time to inject the current datetime,
    enabling accurate resolution of relative date expressions (e.g. 'mañana', 'in 3 days').
    """
    return create_agent(
        llm,
        tools,
        system_prompt=get_reminder_system_prompt(),
        debug=False,
    )
