from ..services.persistence import save_expense, get_expense_summary, save_reminder
from ..services.rag import query_normative_documents


class TravelAssistant:
    def __init__(self):
        self.rules = TravelRulesAgent()
        self.logistics = LogisticsAgent()
        self.budget = BudgetAgent()
        self.itinerary = ItineraryAgent()

    def default_response(self, message: str):
        return {
            "message": (
                "Hola, soy tu asistente de viaje. "
                "Puedes pedirme cosas como 'Anota 20€ en transporte', "
                "'Muéstrame mi presupuesto', 'Consulta requisitos de visa', "
                "o 'Recuérdame check-in mañana 18:00'."
            )
        }


class TravelRulesAgent:
    def consult_rule(self, query: str):
        answer, sources = query_normative_documents(query)
        return {"query": query, "answer": answer, "sources": sources}


class LogisticsAgent:
    def search_logistics(self, query: str):
        return {
            "query": query,
            "results": [
                {
                    "type": "placeholder",
                    "name": "Búsqueda de logística en desarrollo",
                    "description": (
                        "Este módulo se integrará con APIs de vuelo y hotel "
                        "en la siguiente iteración."
                    ),
                }
            ],
        }


class BudgetAgent:
    def record_expense(self, expense_data: dict):
        saved = save_expense(
            description=expense_data["description"],
            amount=expense_data["amount"],
            category=expense_data["category"],
        )
        return {"message": "Gasto registrado", "expense": saved}

    def summary(self):
        summary = get_expense_summary()
        return {"message": "Resumen de gastos", "summary": summary}


class ItineraryAgent:
    def create_reminder(self, reminder_data: dict):
        saved = save_reminder(
            title=reminder_data["title"],
            due_time=reminder_data["due_time"],
            note=reminder_data["note"],
        )
        return {"message": "Recordatorio guardado", "reminder": saved}
