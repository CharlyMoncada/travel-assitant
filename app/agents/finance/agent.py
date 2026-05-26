from langchain.agents import create_agent
from .prompts import FINANCE_AGENT_SYSTEM_PROMPT

def create_finance_agent(llm, tools: list, checkpointer):
    """
    Creates and compiles the sub-agent specialized in Finance and Expenses.
    """
    # Filter only expense and budget tools
    finance_tools = [
        t for t in tools 
        if any(name in t.name for name in ["expense", "budget"])
    ]
    return create_agent(
        llm,
        finance_tools,
        system_prompt=FINANCE_AGENT_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        debug=False,
    )
