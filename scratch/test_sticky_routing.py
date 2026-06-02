import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env con la ruta absoluta del proyecto
dotenv_path = Path("/Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/.env")
load_dotenv(dotenv_path=dotenv_path, override=True)

# Configurar logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_sticky_routing")

async def run_scenario_step(router, message: str, thread_id: str):
    logger.info(f"\n[MENSAJE ENVIADO]: '{message}' (Hilo: {thread_id})")
    res = await router.handle_message(message, thread_id=thread_id)
    logger.info(f"[AGENTE SELECCIONADO]: {res.get('agent_used') or 'specialized_agent (' + str(res.get('llm_tool')) + ')'}")
    logger.info(f"[RESPUESTA CORTA]: {str(res['message'])[:120].replace('\n', ' ')}...")
    if 'tool_response' in res and res['tool_response']:
        messages = res['tool_response'].get('messages', [])
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                logger.info(f"-> Tool Calls realizadas: {msg.tool_calls}")

async def main():
    from app.agents.langchain_agent import LangChainAgentRouter
    router = LangChainAgentRouter()
    
    # ----------------------------------------------------
    # ESCENARIO A: FLUJO DE FINANZAS CON STICKY ROUTING
    # ----------------------------------------------------
    logger.info("\n=== INICIANDO ESCENARIO A: FLUJO DE FINANZAS ===")
    thread_a = "thread_sticky_finance"
    
    # 1. Petición directa que activa finance (Layer 1)
    await run_scenario_step(router, "Gastos", thread_a)
    
    # 2. Petición de seguimiento que debe heredar finance (Layer 2 - Sticky Routing)
    await run_scenario_step(router, "¿Cuánto gasté en total?", thread_a)
    
    # 3. Otra petición de seguimiento corta (Layer 2 - Sticky Routing)
    await run_scenario_step(router, "ver lista", thread_a)

    # ----------------------------------------------------
    # ESCENARIO B: FLUJO DE RECORDATORIOS CON STICKY ROUTING
    # ----------------------------------------------------
    logger.info("\n=== INICIANDO ESCENARIO B: FLUJO DE RECORDATORIOS ===")
    thread_b = "thread_sticky_reminders"
    
    # 1. Petición directa de recordatorios (Layer 1)
    await run_scenario_step(router, "Recordatorios", thread_b)
    
    # 2. Petición de seguimiento para crear recordatorio (Layer 2 - Sticky Routing)
    await run_scenario_step(router, "Crear recordatorio de comprar pan para mañana a las 8", thread_b)
    
    # 3. Petición corta de seguimiento (Layer 2 - Sticky Routing)
    await run_scenario_step(router, "ver lista", thread_b)
    
    await router.stop()

if __name__ == "__main__":
    asyncio.run(main())
