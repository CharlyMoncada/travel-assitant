from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..agents import TravelAssistant
from ..utils.tools import parse_expense_entry, parse_reminder_entry

TOOL_DEFINITIONS = {
    "expense": "Registrar un gasto en el sistema de finanzas.",
    "reminder": "Crear un recordatorio o tarea en el gestor de itinerario.",
    "budget": "Generar un resumen del presupuesto y gastos registrados.",
    "rules": "Responder consultas sobre normativa, visas y documentación de viaje.",
    "logistics": "Buscar opciones de vuelo, hotel o logística (placeholder).",
    "default": "Responder con ayuda general o indicar cómo usar el asistente.",
}


@dataclass
class MCPTool:
    name: str
    description: str
    func: Callable[[str], Any]
    examples: List[str] = field(default_factory=list)

    def invoke(self, user_input: str) -> Any:
        return self.func(user_input)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "examples": self.examples,
        }


def _parse_and_record_expense(assistant: TravelAssistant, text_or_payload: Any) -> Any:
    if isinstance(text_or_payload, dict):
        expense = text_or_payload
    else:
        expense = parse_expense_entry(text_or_payload)

    if expense:
        return assistant.budget.record_expense(expense)
    return {
        "message": "No pude interpretar el gasto. Usa un formato como 'Anota 20€ en transporte'."
    }


def _parse_and_create_reminder(assistant: TravelAssistant, text_or_payload: Any) -> Any:
    if isinstance(text_or_payload, dict):
        reminder = text_or_payload
    else:
        reminder = parse_reminder_entry(text_or_payload)

    if reminder:
        return assistant.itinerary.create_reminder(reminder)
    return {
        "message": "No pude interpretar el recordatorio. Usa un formato como 'Recuérdame check-in mañana 18:00'."
    }


def register_default_mcp_tools(mcp_server: Any, assistant: TravelAssistant) -> None:
    mcp_server.register_tool(
        "expense",
        TOOL_DEFINITIONS["expense"],
        lambda text: _parse_and_record_expense(assistant, text),
        ["Anota 20€ en taxi", "Registra 15€ en comidas"],
    )
    mcp_server.register_tool(
        "reminder",
        TOOL_DEFINITIONS["reminder"],
        lambda text: _parse_and_create_reminder(assistant, text),
        ["Recuérdame hacer el check-in mañana", "Agrega recordatorio para comprar seguro"],
    )
    mcp_server.register_tool(
        "budget",
        TOOL_DEFINITIONS["budget"],
        lambda text: assistant.budget.summary(),
        ["Muéstrame mi presupuesto", "Resumen de gastos"],
    )
    mcp_server.register_tool(
        "rules",
        TOOL_DEFINITIONS["rules"],
        lambda text: assistant.rules.consult_rule(text),
        ["¿Qué visa necesito para Italia?", "Requisitos de entrada a España"],
    )
    mcp_server.register_tool(
        "logistics",
        TOOL_DEFINITIONS["logistics"],
        lambda text: assistant.logistics.search_logistics(text),
        ["Busca vuelos a Madrid", "Necesito hotel en Roma"],
    )
    mcp_server.register_tool(
        "default",
        TOOL_DEFINITIONS["default"],
        lambda text: assistant.default_response(text),
        ["Hola", "¿Qué puedes hacer?"],
    )
