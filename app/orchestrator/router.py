from ..utils.tools import parse_expense_entry, parse_reminder_entry
from ..services.llm import extract_intent_payload, render_llm_response, route_tool


class MessageRouter:
    def __init__(self, assistant, mcp_service=None):
        self.assistant = assistant
        self.mcp_service = mcp_service

    def handle_message(self, message: str):
        if self.mcp_service:
            return self.mcp_service.execute(message)

        extraction = extract_intent_payload(message)
        if extraction:
            tool_name = extraction["intent"]
            tool_input = extraction if tool_name in {"expense", "reminder"} else extraction.get("input", message)
            response = self._invoke_tool(tool_name, tool_input)
            if isinstance(response, dict):
                llm_text = render_llm_response(message, tool_name, response)
                result = {
                    "llm_used": True,
                    "llm_tool": tool_name,
                    "tool_response": response,
                    "message": llm_text if llm_text else response.get("message", str(response)),
                }
                return result
            return {
                "llm_used": True,
                "llm_tool": tool_name,
                "message": str(response),
                "tool_response": response,
            }

        llm_route = route_tool(message)
        if llm_route:
            tool_name = llm_route["tool"]
            tool_input = llm_route["input"]
            response = self._invoke_tool(tool_name, tool_input)
            if isinstance(response, dict):
                llm_text = render_llm_response(message, tool_name, response)
                result = {
                    "llm_used": True,
                    "llm_tool": tool_name,
                    "tool_response": response,
                    "message": llm_text if llm_text else response.get("message", str(response)),
                }
                return result
            return {
                "llm_used": True,
                "llm_tool": tool_name,
                "message": str(response),
                "tool_response": response,
            }

        return self._handle_rule_based(message)

    def _invoke_tool(self, tool_name: str, user_input: str):
        if tool_name == "expense":
            if isinstance(user_input, dict):
                expense = user_input
            else:
                expense = parse_expense_entry(user_input)
            if expense:
                return self.assistant.budget.record_expense(expense)
            return {
                "message": "No pude interpretar el gasto. Usa un formato como 'Anota 20€ en transporte'."
            }

        if tool_name == "reminder":
            if isinstance(user_input, dict):
                reminder = user_input
            else:
                reminder = parse_reminder_entry(user_input)
            if reminder:
                return self.assistant.itinerary.create_reminder(reminder)
            return {
                "message": "No pude interpretar el recordatorio. Usa un formato como 'Recuérdame check-in mañana 18:00'."
            }

        if tool_name == "budget":
            return self.assistant.budget.summary()

        if tool_name == "rules":
            return self.assistant.rules.consult_rule(user_input)

        if tool_name == "logistics":
            return self.assistant.logistics.search_logistics(user_input)

        return self.assistant.default_response(user_input)

    def _handle_rule_based(self, message: str):
        text = message.lower().strip()

        reminder_keywords = ["recordatorio", "recuerda", "recuérdame", "recuerdame", "recordar"]
        if any(keyword in text for keyword in reminder_keywords):
            reminder = parse_reminder_entry(message)
            if reminder:
                return self.assistant.itinerary.create_reminder(reminder)
            return {
                "message": "No pude interpretar el recordatorio. Usa un formato como 'Recuérdame check-in mañana 18:00'."
            }

        expense = parse_expense_entry(message)
        if expense:
            return self.assistant.budget.record_expense(expense)

        if "presupuesto" in text or "gastos" in text or "reporte" in text or "saldo" in text:
            return self.assistant.budget.summary()

        if "visa" in text or "normativa" in text or "documentos" in text or "requisitos" in text:
            return self.assistant.rules.consult_rule(message)

        if "vuelo" in text or "hotel" in text or "alojamiento" in text:
            return self.assistant.logistics.search_logistics(message)

        return self.assistant.default_response(message)
