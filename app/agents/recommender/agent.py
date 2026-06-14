from langchain.agents import create_agent

from .prompts import RECOMMENDER_SYSTEM_PROMPT


def create_recommender_agent(llm, tools: list, checkpointer):
    """
    Creates and compiles the sub-agent specialized in travel packing recommendations.

    Uses weather data and the default packing list to classify items into
    mandatory, recommended, and discarded categories for the given destination.
    """
    return create_agent(
        llm,
        tools,
        system_prompt=RECOMMENDER_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        debug=False,
    )
