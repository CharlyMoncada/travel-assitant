from langchain.agents import create_agent
from .prompts import get_reminder_system_prompt

def create_reminder_agent(llm, tools: list):
    """
    Crea y compila el subagente especializado en Recordatorios y Tareas.
    El prompt del sistema se genera en el momento de la llamada para inyectar la fecha y hora actuales,
    permitiendo la resolución precisa de expresiones de fecha relativas (ej. 'mañana', 'in 3 days').
    """
    return create_agent(
        llm,
        tools,
        system_prompt=get_reminder_system_prompt(),
        debug=False,
    )
