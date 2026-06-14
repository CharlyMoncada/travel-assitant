import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env con la ruta absoluta del proyecto
dotenv_path = Path("/Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/.env")
load_dotenv(dotenv_path=dotenv_path, override=True)

# Configurar logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_out_of_scope")

async def test_query(router, query: str, thread_id: str):
    logger.info(f"\n==================================================")
    logger.info(f"PROBANDO CONSULTA: '{query}'")
    logger.info(f"==================================================")
    try:
        res = await router.handle_message(query, thread_id=thread_id)
        logger.info(f"RESPUESTA FINAL DEL AGENTE:\n{res.get('message')}")
        logger.info(f"Agente Usado: {res.get('agent_used')}")
        logger.info(f"¿Usa LLM?: {res.get('llm_used')}")
    except Exception as e:
        logger.exception(f"Error procesando consulta '{query}'")

async def main():
    sys.path.append(os.getcwd())
    from app.agents.orchestrator import TravelAgentOrchestrator
    router = TravelAgentOrchestrator()
    
    # 1. Fuera de ámbito en español (Compra de auto)
    await test_query(router, "Que auto es bueno para comprar?", "thread_out_1")
    
    # 2. Fuera de ámbito en inglés (Compra de auto)
    await test_query(router, "What is a good car to buy?", "thread_out_2")
    
    # 3. Fuera de ámbito general (Programación)
    await test_query(router, "How can I write a quicksort in Python?", "thread_out_3")
    
    # 4. En ámbito (Recordatorio)
    await test_query(router, "Recordatorio de comprar pan mañana a las 8am", "thread_in_1")
    
    # 5. En ámbito (Normativas/General RAG)
    await test_query(router, "¿Cuáles son los requisitos de visado para entrar a Italia?", "thread_in_2")
    
    # Cerrar conexiones
    await router.stop()

if __name__ == "__main__":
    asyncio.run(main())
