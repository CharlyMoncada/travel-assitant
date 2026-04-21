from typing import Any, Callable, Dict, List, Optional

from ..agents import TravelAssistant
from ..services.llm import extract_intent_payload, render_llm_response, route_tool
from ..utils.tools import parse_expense_entry, parse_reminder_entry
from .mcp_tools import MCPTool, register_default_mcp_tools


class MCPServer:
    def __init__(self, assistant: TravelAssistant):
        self.assistant = assistant
        self.tools: Dict[str, MCPTool] = {}
        register_default_mcp_tools(self, assistant)

    def register_tool(
        self,
        name: str,
        description: str,
        func: Callable[[str], Any],
        examples: Optional[List[str]] = None,
    ) -> None:
        self.tools[name] = MCPTool(
            name=name,
            description=description,
            func=func,
            examples=examples or [],
        )

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in self.tools.values()]

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        return self.tools.get(tool_name)

    def status(self) -> Dict[str, Any]:
        return {
            "tool_count": len(self.tools),
            "tools": list(self.tools.keys()),
        }

    def execute(self, user_message: str) -> Dict[str, Any]:
        extraction = extract_intent_payload(user_message)
        if extraction and extraction["intent"] != "default":
            tool = self.get_tool(extraction["intent"])
            if tool:
                if extraction["intent"] in {"expense", "reminder"}:
                    tool_input = extraction
                else:
                    tool_input = extraction.get("input", user_message)
                return self._invoke_tool(tool, tool_input, user_message)

        route = route_tool(user_message)
        if route and route["tool"] != "default":
            tool = self.get_tool(route["tool"])
            if tool:
                return self._invoke_tool(tool, route["input"], user_message)

        fallback = self._fallback_rule_based(user_message)
        if fallback is not None:
            return fallback

        return self._fallback(user_message)

    def _fallback_rule_based(self, user_message: str) -> Optional[Dict[str, Any]]:
        text = user_message.lower().strip()

        reminder_keywords = ["recordatorio", "recuerda", "recuérdame", "recuerdame", "recordar"]
        if any(keyword in text for keyword in reminder_keywords):
            reminder = parse_reminder_entry(user_message)
            if reminder:
                tool = self.get_tool("reminder")
                if tool:
                    return self._invoke_tool(tool, reminder, user_message)

        expense = parse_expense_entry(user_message)
        if expense:
            tool = self.get_tool("expense")
            if tool:
                return self._invoke_tool(tool, expense, user_message)

        if any(keyword in text for keyword in ["presupuesto", "gastos", "reporte", "saldo"]):
            tool = self.get_tool("budget")
            if tool:
                return self._invoke_tool(tool, user_message, user_message)

        if any(keyword in text for keyword in ["visa", "normativa", "documentos", "requisitos"]):
            tool = self.get_tool("rules")
            if tool:
                return self._invoke_tool(tool, user_message, user_message)

        if any(keyword in text for keyword in ["vuelo", "hotel", "alojamiento"]):
            tool = self.get_tool("logistics")
            if tool:
                return self._invoke_tool(tool, user_message, user_message)

        return None

    def _invoke_tool(self, tool: MCPTool, user_input: str, user_message: str) -> Dict[str, Any]:
        result = tool.invoke(user_input)
        response = {
            "llm_used": True,
            "llm_tool": tool.name,
            "tool_response": result,
        }

        if isinstance(result, dict):
            llm_text = render_llm_response(user_message, tool.name, result)
            response["message"] = llm_text if llm_text else result.get("message", str(result))
        else:
            response["message"] = str(result)

        return response

    def _fallback(self, user_message: str) -> Dict[str, Any]:
        default_response = self.assistant.default_response(user_message)
        return {
            "llm_used": False,
            "llm_tool": None,
            "tool_response": None,
            "message": default_response["message"],
        }
