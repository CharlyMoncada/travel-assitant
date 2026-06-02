import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Configurar logs para ver toda la telemetría e inspecciones
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_stress_history")

# Cargar .env con la ruta absoluta del proyecto
dotenv_path = Path("/Users/carlosmoncada/Documents/code/master/tfm/travel-assitant/.env")
load_dotenv(dotenv_path=dotenv_path, override=True)

sys.path.append(os.getcwd())

async def run_scenario(router, message: str, thread_id: str):
    logger.info(f"\n" + "="*80)
    logger.info(f"ENVIANDO CONSULTA DE STRESS: '{message}'")
    logger.info(f"="*80)
    try:
        res = await router.handle_message(message, thread_id=thread_id)
        logger.info(f"RESPUESTA FINAL RECIBIDA: '{res['message']}'")
        logger.info(f"LLM UTILIZADO: {res.get('llm_used')}")
        logger.info(f"LLM TOOL / RUTA: {res.get('llm_tool')}")
    except Exception as e:
        logger.exception(f"¡FALLO DETECTADO! Error durante el procesamiento: {e}")
        raise e

async def main():
    from app.agents.langchain_agent import LangChainAgentRouter
    router = LangChainAgentRouter()
    
    thread_id = "stress_integration_test_thread"
    
    # Lista de 14 interacciones consecutivas (Stress Test) que forzarán múltiples podas por turnos.
    # Alternamos charla, gastos, recordatorios, normativa y preguntas generales.
    interactions = [
        "Hola, buenos días. ¿Qué tal?",  # Turno 1
        "Me gustaría saber en qué me puedes ayudar",  # Turno 2
        "¿Cuáles son los requisitos de visa para viajar a España?",  # Turno 3 (RAG/General)
        "Puedes decirme los gastos que tengo guardados",  # Turno 4 (Gastos) -> Poda se activará en los próximos turnos
        "Quiero agregar un gasto de 25 euros para una cena",  # Turno 5 (Gastos)
        "Dime mis recordatorios por favor",  # Turno 6 (Recordatorios)
        "Recordatorio de viaje para mañana a la tarde",  # Turno 7 (Recordatorios)
        "¿Qué vacunas necesito para viajar a España?",  # Turno 8 (RAG/General)
        "Hola de nuevo, ¿me recuerdas de qué estábamos hablando?",  # Turno 9 (Charla, verificará que el historial siga siendo coherente tras múltiples podas)
        "Muéstrame mis gastos otra vez",  # Turno 10 (Gastos)
        "¿Cuáles son las reglas de equipaje para viajar?",  # Turno 11 (General)
        "Quiero crear otro recordatorio para comprar los billetes",  # Turno 12 (Recordatorios)
        "Gracias, eres de gran ayuda",  # Turno 13 (Charla)
        "Adiós, que pases un buen día"  # Turno 14 (Charla)
    ]
    
    logger.info("Comenzando Stress Test de Poda Conversacional por Turnos...")
    
    for idx, msg in enumerate(interactions):
        logger.info(f"\n>>> INTERACCIÓN CONSECUTIVA {idx+1}/{len(interactions)} <<<")
        await run_scenario(router, msg, thread_id)
        # Pequeña espera para no saturar
        await asyncio.sleep(0.5)
        
    # Cerrar de forma limpia las conexiones persistentes
    await router.stop()
        
    logger.info("\n" + "="*80)
    logger.info("¡STRESS TEST FINALIZADO CON ÉXITO! Sin ninguna excepción 400.")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(main())
