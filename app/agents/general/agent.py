from langchain.agents import create_agent
from .prompts import GENERAL_AGENT_SYSTEM_PROMPT

def create_general_agent(llm, tools: list, checkpointer):
    """
    Creates and compiles the sub-agent specialized in Regulations and Logistics.
    """
    return create_agent(
        llm,
        tools,  # Receives local tools (rules, logistics)
        system_prompt=GENERAL_AGENT_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        debug=False,
    )
