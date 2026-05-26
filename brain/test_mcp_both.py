import asyncio
import logging
from mcp import ClientSession
from mcp.client.sse import sse_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_mcp_both")

async def test_server(name, url):
    logger.info(f"--- Probando servidor MCP {name} en: {url} ---")
    try:
        async with sse_client(url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info(f"Conexión inicializada con éxito para {name}.")
                tools_list = await session.list_tools()
                tools_names = [t.name for t in tools_list.tools]
                logger.info(f"Herramientas encontradas en {name}: {tools_names}")
                return True
    except Exception as e:
        logger.error(f"Error al conectar con el servidor MCP {name}: {e}")
        return False

async def main():
    res_finance = await test_server("Gastos", "http://localhost:8002/sse")
    res_reminder = await test_server("Recordatorios", "http://localhost:8003/sse")
    logger.info(f"Resumen de pruebas: Gastos={'OK' if res_finance else 'FAIL'}, Recordatorios={'OK' if res_reminder else 'FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
