from langchain.agents import create_agent
from .prompts import get_finance_system_prompt

def create_finance_agent(llm, tools: list):
    """
    Creates and compiles the sub-agent specialized in Finance and Expenses.
    """
    return create_agent(
        llm,
        tools,
        system_prompt=get_finance_system_prompt(),
        debug=False,
    )
