import asyncio
import logging
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, RemoveMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_prune_turns")

def prune_history_by_turns(current_messages: list, max_turns: int = 3) -> list:
    """
    Simula la nueva lógica de poda basada en turnos de usuario completos.
    """
    human_indices = [i for i, msg in enumerate(current_messages) if isinstance(msg, HumanMessage)]
    logger.info(f"Índices de HumanMessage en el historial: {human_indices}")
    
    if len(human_indices) > max_turns:
        # Mantener los últimos `max_turns` turnos
        keep_from_index = human_indices[-max_turns]
        messages_to_remove = current_messages[:keep_from_index]
        logger.info(f"Podando desde el inicio hasta el índice {keep_from_index}. Eliminando {len(messages_to_remove)} mensajes.")
        removals = [RemoveMessage(id=msg.id) for msg in messages_to_remove if msg.id]
        return removals
    return []

def main():
    # Simulamos un historial con 4 turnos de usuario, donde algunos turnos tienen function calling
    history = [
        # Turno 1 (Viejo)
        HumanMessage(content="Hola", id="msg1"),
        AIMessage(content="Hola, ¿en qué puedo ayudarte?", id="msg2"),
        
        # Turno 2 (Viejo, con function calling)
        HumanMessage(content="¿Qué gastos tengo?", id="msg3"),
        AIMessage(content="", tool_calls=[{"name": "query_expenses", "args": {}, "id": "call1"}], id="msg4"),
        ToolMessage(content="Tienes un gasto de 10€", tool_call_id="call1", id="msg5"),
        AIMessage(content="Tienes un gasto de 10€ guardado.", id="msg6"),
        
        # Turno 3 (Reciente)
        HumanMessage(content="Ponme un recordatorio de viaje", id="msg7"),
        AIMessage(content="", tool_calls=[{"name": "record_reminder", "args": {"title": "Viaje"}, "id": "call2"}], id="msg8"),
        ToolMessage(content="Recordatorio creado", tool_call_id="call2", id="msg9"),
        AIMessage(content="¡Hecho! Recordatorio creado para tu viaje.", id="msg10"),
        
        # Turno 4 (Actual)
        HumanMessage(content="Si un recordatorio de viaje para mañana a la tarde", id="msg11")
    ]
    
    logger.info(f"Total mensajes iniciales: {len(history)}")
    removals = prune_history_by_turns(history, max_turns=3)
    logger.info(f"Removals generados (Total: {len(removals)}):")
    for r in removals:
        logger.info(f"  RemoveMessage id: {r.id}")
        
    # Aplicar la eliminación para ver qué queda
    remaining = [m for m in history if m.id not in [r.id for r in removals]]
    logger.info(f"Mensajes restantes (Total: {len(remaining)}):")
    for idx, m in enumerate(remaining):
        logger.info(f"  [{idx}] type: {m.type}, id: {m.id}, class: {m.__class__.__name__}, content: '{m.content[:30]}'")

if __name__ == "__main__":
    main()
