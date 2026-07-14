from langchain.agents import create_agent
from .prompts import get_general_system_prompt
from .tools import get_general_tools

def create_general_agent(llm):
    """
    Creates and compiles the sub-agent specialized in Regulations and Logistics.
    """
    tools = get_general_tools()
    return create_agent(
        llm,
        tools, 
        system_prompt=get_general_system_prompt(),
        debug=False,
    )
