from langchain.agents import create_agent

from .prompts import RECOMMENDER_SYSTEM_PROMPT
from .tools import get_recommender_tools


def create_recommender_agent(llm):
    """
    Creates and compiles the sub-agent specialized in travel packing recommendations.

    Uses weather data and the default packing list to classify items into
    mandatory, recommended, and discarded categories for the given destination.
    """
    tools = get_recommender_tools()
    return create_agent(
        llm,
        tools,
        system_prompt=RECOMMENDER_SYSTEM_PROMPT,
        debug=False,
    )
