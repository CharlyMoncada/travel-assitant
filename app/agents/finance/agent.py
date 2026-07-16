from langchain.agents import create_agent
from .prompts import get_finance_system_prompt

def create_finance_agent(llm, tools: list):
    """
    Crea y compila el subagente especializado en Finanzas y Gastos.
    """
    return create_agent(
        llm,
        tools,
        system_prompt=get_finance_system_prompt(),
        debug=False,
    )
