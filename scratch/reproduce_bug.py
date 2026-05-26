import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Configurar logging para ver todo
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("reproduce_bug")

# Cargar .env con la ruta absoluta del proyecto
dotenv_path = Path("/Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/.env")
load_dotenv(dotenv_path=dotenv_path, override=True)

sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from app.agents.langchain_agent import LangChainAgentRouter
from app.services.llm import get_openai_model

async def test():
    router = LangChainAgentRouter()
    llm = ChatOpenAI(model_name=get_openai_model(), temperature=0.0)
    config = {"configurable": {"thread_id": "test_thread_bug"}}
    
    # 1. Crear un agente temporal para inicializar la memoria y meter mensajes
    from langchain.agents import create_agent
    temp_agent = create_agent(llm, [], system_prompt="", checkpointer=router.memory)
    
    # 2. Vamos a insertar mensajes simulados que representan un historial típico con herramientas
    # Queremos insertar más de 8 mensajes para forzar la poda.
    # Un historial de 10 mensajes:
    messages_to_insert = [
        HumanMessage(content="Hola", id="msg1"),
        AIMessage(content="Hola, ¿en qué puedo ayudarte?", id="msg2"),
        HumanMessage(content="¿Qué gastos tengo?", id="msg3"),
        AIMessage(content="", tool_calls=[{"name": "query_expenses", "args": {}, "id": "call1"}], id="msg4"),
        ToolMessage(content="Tienes un gasto de 10€", tool_call_id="call1", id="msg5"),
        AIMessage(content="Tienes un gasto de 10€ guardado.", id="msg6"),
        HumanMessage(content="Ponme un recordatorio de viaje", id="msg7"),
        AIMessage(content="", tool_calls=[{"name": "record_reminder", "args": {"title": "Viaje"}, "id": "call2"}], id="msg8"),
        ToolMessage(content="Recordatorio creado", tool_call_id="call2", id="msg9"),
        AIMessage(content="¡Hecho! Recordatorio creado para tu viaje.", id="msg10"),
    ]
    
    logger.info("Insertando mensajes iniciales en el checkpointer...")
    await temp_agent.aupdate_state(config, {"messages": messages_to_insert}, as_node="model")
    
    # Comprobar mensajes actuales en el estado antes de la poda
    state = await temp_agent.aget_state(config)
    current_msgs = state.values.get("messages", [])
    logger.info(f"Mensajes antes de la poda (Total: {len(current_msgs)}):")
    for idx, m in enumerate(current_msgs):
        logger.info(f"  [{idx}] type: {m.type}, id: {m.id}, class: {m.__class__.__name__}")
        
    # 3. Ejecutar poda
    logger.info("Ejecutando poda...")
    await router._prune_history_if_needed(temp_agent, config, "test_thread_bug")
    
    # Comprobar mensajes actuales en el estado después de la poda
    state = await temp_agent.aget_state(config)
    current_msgs_after = state.values.get("messages", [])
    logger.info(f"Mensajes después de la poda (Total: {len(current_msgs_after)}):")
    for idx, m in enumerate(current_msgs_after):
        logger.info(f"  [{idx}] type: {m.type}, id: {m.id}, class: {m.__class__.__name__}")
        
    # 4. Obtener historial limpio para el supervisor
    logger.info("Obteniendo historial limpio para el supervisor...")
    history = await router._get_clean_history(temp_agent, config)
    logger.info(f"Historial limpio (Total: {len(history)}):")
    for idx, m in enumerate(history):
        logger.info(f"  [{idx}] type: {m.type}, id: {m.id}, class: {m.__class__.__name__}, content: '{m.content[:30]}'")
        
    # 5. Invocar al supervisor con el historial limpio
    from app.agents.supervisor import run_supervisor
    logger.info("Invocando al supervisor...")
    try:
        route, supervisor_text = await run_supervisor(llm, history, "Si un recordatorio de viaje para mañana a la tarde")
        logger.info(f"¡Éxito! Supervisor respondió ruta: {route}, texto: {supervisor_text}")
    except Exception as e:
        logger.exception("Error al invocar al supervisor:")

if __name__ == "__main__":
    asyncio.run(test())
