from langchain.agents import create_agent
from .prompts import get_general_system_prompt
from .tools import get_general_tools

def create_general_agent(llm):
    """
    Crea y compila el subagente especializado en Normativas y Logística.
    """
    tools = get_general_tools()
    return create_agent(
        llm,
        tools, 
        system_prompt=get_general_system_prompt(),
        debug=False,
    )
