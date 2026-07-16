import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable

from app.services.llm import get_openai_model
from app.services.persistence.conversation_persistence import save_message
from app.services.persistence.memory_persistence import format_user_memories

from ..supervisor import run_supervisor
from .guardrails_input import (
    check_input_guardrail,
    REJECTION_MESSAGE_LANGUAGE,
    REJECTION_MESSAGE_INJECTION,
)
from .guardrails_output import (
    check_output_integrity,
    REJECTION_MESSAGE_OUTPUT_LEAK,
    REJECTION_MESSAGE_OUTPUT_ERROR,
)
from .mcp_client import MCPConnectionManager
from .mcp_schema import MCPSchemaTranslator
from .history_manager import ChatMemoryService
from .agent_executor import SubAgentExecutor

logger = logging.getLogger(__name__)


class TravelAgentOrchestrator:
    """
    Orquestador basado en LangChain que actúa como cliente multiservidor para el Model Context Protocol (MCP).
    Delega la conectividad, traducción, ejecución y persistencia de memoria a subcomponentes especializados.
    """

    def __init__(self):
        self.mcp_manager = MCPConnectionManager()

    @property
    def mcp_servers(self) -> list[str]:
        return self.mcp_manager.mcp_servers

    @property
    def sessions(self) -> list:
        return self.mcp_manager.sessions

    @sessions.setter
    def sessions(self, value):
        self.mcp_manager.sessions = value

    async def get_sessions(self):
        return await self.mcp_manager.get_sessions()

    async def stop(self):
        await self.mcp_manager.stop()

    def _save_long_term_memory_if_needed(self, thread_id: str, message: str) -> None:
        """Delega la detección y persistencia de memoria a largo plazo a ChatMemoryService."""
        ChatMemoryService.save_long_term_memory_if_needed(thread_id, message)


    @traceable(name="travel_assistant_handle_message")
    async def handle_message(
        self,
        message: str,
        thread_id: str = "default",
    ) -> dict[str, Any]:
        logger.info(
            "Agent receives message: '%s' (thread: '%s')",
            message,
            thread_id,
        )

        # Primero, intentar guardar el mensaje del usuario en el historial
        try:
            save_message(thread_id, "user", message)
        except Exception as e:
            logger.warning(
                "Could not persist user message at startup for thread '%s': %s",
                thread_id,
                e,
                exc_info=True,
            )

        # Guardarraíl global: verificación híbrida de idioma e inyección (prefiltro regex + LLM)
        lang_ok, is_safe, block_reason = await check_input_guardrail(message)

        if not lang_ok:
            logger.info("Input guardrail blocked: wrong language (reason='%s')", block_reason)
            try:
                save_message(thread_id, "assistant", REJECTION_MESSAGE_LANGUAGE)
            except Exception as e:
                logger.warning("Could not persist language rejection message: %s", e)
            return {
                "llm_used": True,
                "llm_tool": "input_guardrail_language",
                "agent_used": "global_guardrail",
                "tool_response": None,
                "message": REJECTION_MESSAGE_LANGUAGE,
            }

        if not is_safe:
            logger.warning("Input guardrail blocked: injection detected (reason='%s')", block_reason)
            try:
                save_message(thread_id, "assistant", REJECTION_MESSAGE_INJECTION)
            except Exception as e:
                logger.warning("Could not persist injection rejection message: %s", e)
            return {
                "llm_used": True,
                "llm_tool": "input_guardrail_injection",
                "agent_used": "global_guardrail",
                "tool_response": None,
                "message": REJECTION_MESSAGE_INJECTION,
            }

        # Si ambos guardarraíles han pasado, extraer/guardar la memoria a largo plazo si es necesario
        try:
            self._save_long_term_memory_if_needed(thread_id, message)
        except Exception as e:
            logger.warning(
                "Could not persist memory at startup for thread '%s': %s",
                thread_id,
                e,
                exc_info=True,
            )

        try:
            langchain_tools_by_server = await self.mcp_manager.discover_mcp_tools()

            llm = ChatOpenAI(
                model_name=get_openai_model(),
                temperature=0.0,
            )

            config = {"configurable": {"thread_id": thread_id}}

            history = ChatMemoryService.get_persistent_history(
                thread_id,
                limit=20,
            )

            long_term_memory_text = format_user_memories(thread_id)

            message_for_supervisor = ChatMemoryService.build_memory_context_for_agent(
                thread_id=thread_id,
                short_term_memory_text="",
                long_term_memory_text=long_term_memory_text,
                message=message,
            )

            # Eliminar el último mensaje del historial si es el mensaje actual del usuario
            # que ya guardamos en la base de datos. Esto evita duplicarlo
            # en supervisor_messages.
            supervisor_history = list(history)
            if supervisor_history and isinstance(supervisor_history[-1], HumanMessage):
                supervisor_history.pop()

            routes, supervisor_text = await run_supervisor(
                llm,
                supervisor_history,
                message_for_supervisor,
            )

            if not routes:
                logger.info("Supervisor assumes direct interaction.")

                final_message = MCPSchemaTranslator.extract_message(supervisor_text)

                # Verificación de integridad de salida
                is_output_safe, output_failure_reason = await check_output_integrity(final_message)
                if not is_output_safe:
                    logger.warning("Output guardrail blocked supervisor response (reason='%s')", output_failure_reason)
                    final_message = (
                        REJECTION_MESSAGE_OUTPUT_ERROR
                        if output_failure_reason == "raw_error_leak"
                        else REJECTION_MESSAGE_OUTPUT_LEAK
                    )

                try:
                    save_message(thread_id, "assistant", final_message)
                except Exception as e:
                    logger.warning(
                        "Could not persist supervisor conversation: %s",
                        e,
                        exc_info=True,
                    )

                return {
                    "llm_used": True,
                    "llm_tool": "supervisor_chat" if is_output_safe else "output_integrity_guardrail",
                    "agent_used": "supervisor",
                    "tool_response": None,
                    "message": final_message,
                }

            logger.info("Routing request to specialized sub-agents: %s", routes)

            responses = []
            last_agent_response = None

            # Capturar el snapshot inicial de memoria a corto plazo una sola vez
            short_term_memory_text = ChatMemoryService.format_persistent_memory(
                thread_id,
                limit=20,
            )

            message_for_agent = ChatMemoryService.build_memory_context_for_agent(
                thread_id=thread_id,
                short_term_memory_text=short_term_memory_text,
                long_term_memory_text=long_term_memory_text,
                message=message,
            )

            # Tarea corrutina para ejecutar una ruta individual de forma concurrente
            async def run_single_route(route: str):
                logger.info("Concurrent Routing: launching execution for sub-agent '%s'", route)
                agent_res, out = await SubAgentExecutor.run_specialized_agent(
                    llm,
                    route,
                    message_for_agent,
                    config,
                    langchain_tools_by_server
                )
                ext = MCPSchemaTranslator.extract_message(out)

                # Verificación de integridad de salida para la respuesta individual del agente
                is_safe_out, fail_reason = await check_output_integrity(ext)
                if not is_safe_out:
                    logger.warning("Output guardrail blocked agent response (reason='%s')", fail_reason)
                    ext = (
                        REJECTION_MESSAGE_OUTPUT_ERROR
                        if fail_reason == "raw_error_leak"
                        else REJECTION_MESSAGE_OUTPUT_LEAK
                    )
                return agent_res, ext

            # Ejecutar todas las tareas de forma concurrente
            tasks = [run_single_route(r) for r in routes]
            results = await asyncio.gather(*tasks)

            # Persistir las respuestas secuencialmente para mantener el historial de SQLite consistente
            for agent_response, extracted in results:
                try:
                    save_message(thread_id, "assistant", extracted)
                except Exception as e:
                    logger.warning("Could not persist intermediate agent response: %s", e)

                responses.append(extracted)
                last_agent_response = agent_response

            final_message = "\n\n".join(responses)

        except Exception as exc:
            logger.exception(
                "Exception during TravelAgentOrchestrator execution: %s",
                exc,
            )

            error_message = (
                f"Error connecting to MCP tool servers. "
                f"Please make sure independent servers are started: "
                f"{', '.join(self.mcp_servers)}. "
                f"(Technical detail: {str(exc)})"
            )

            try:
                save_message(thread_id, "assistant", error_message)
            except Exception:
                pass

            return {
                "llm_used": False,
                "llm_tool": None,
                "agent_used": "unknown",
                "tool_response": None,
                "message": error_message,
            }

        return {
            "llm_used": True,
            "llm_tool": "langchain_agent_via_mcp",
            "agent_used": ", ".join(routes),
            "tool_response": last_agent_response,
            "message": final_message,
        }
