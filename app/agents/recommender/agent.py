from langchain.agents import create_agent

from .prompts import get_recommender_system_prompt
from .tools import get_recommender_tools


def create_recommender_agent(llm):
    """
    Crea y compila el subagente especializado en recomendaciones de equipaje de viaje.

    Usa datos meteorológicos y la lista de equipaje predeterminada para clasificar artículos en
    categorías obligatorio, recomendado y descartado para el destino indicado.
    """
    tools = get_recommender_tools()
    return create_agent(
        llm,
        tools,
        system_prompt=get_recommender_system_prompt(),
        debug=False,
    )
