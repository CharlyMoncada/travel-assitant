import re
from typing import Optional


EXPENSE_KEYWORDS = [
    "gasto",
    "gastos",
    "anota",
    "registra",
    "paga",
    "pago",
    "pagado",
    "compra",
    "comprar",
    "tarifa",
    "cobro",
]
CURRENCY_PATTERN = r"(?:€|eur|euros?|dólares?|dolares?|\$)"
CATEGORY_PATTERN = r"(?:en|para|de)\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)*)"

REMINDER_TITLES = {
    "check-in": "Check-in",
    "check in": "Check-in",
    "vuelo": "Vuelo",
    "hotel": "Hotel",
    "taxi": "Taxi",
    "seguro": "Seguro de viaje",
    "equipaje": "Equipaje",
}

DUE_TIME_PATTERNS = [
    r"\b(hoy|mañana)(?:\s*(?:a\s+las?|a|por\s+la)\s*(\d{1,2}[:h]\d{2}))?\b",
    r"\b(el\s+\d{1,2}\s+de\s+[a-zñ]+(?:\s+de\s+\d{2,4})?)\b",
    r"\b(el\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",
    r"\b(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b",
    r"\b(esta\s+semana|el\s+próximo\s+\w+|el\s+próximo\s+\w+)\b",
]


def _normalize_amount(amount_str: str) -> Optional[float]:
    if "." in amount_str and "," in amount_str:
        normalized = amount_str.replace(".", "").replace(",", ".")
    else:
        normalized = amount_str.replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _has_expense_context(text: str) -> bool:
    if re.search(CURRENCY_PATTERN, text):
        return True
    return any(keyword in text for keyword in EXPENSE_KEYWORDS)


def parse_expense_entry(text: str) -> Optional[dict]:
    lowered = text.lower()
    if not _has_expense_context(lowered):
        return None

    amount_match = re.search(r"(\d+(?:[\.,]\d{1,2})?)\s*(?:" + CURRENCY_PATTERN + r")?", text, re.IGNORECASE)
    if not amount_match:
        return None

    amount = _normalize_amount(amount_match.group(1))
    if amount is None or amount <= 0:
        return None

    category_match = re.search(CATEGORY_PATTERN, text, re.IGNORECASE)
    category = category_match.group(1).strip() if category_match else "otro"

    description = text.strip()
    return {"description": description, "amount": amount, "category": category}


def _extract_due_time(text: str) -> Optional[str]:
    lowered = text.lower()
    for pattern in DUE_TIME_PATTERNS:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if not match:
            continue

        if pattern == DUE_TIME_PATTERNS[0]:
            anchor = match.group(1)
            clock = match.group(2)
            if clock:
                return f"{anchor} {clock.replace('h', ':')}"
            return anchor

        return match.group(0).strip()
    return None


def _extract_reminder_title(text: str) -> str:
    lowered = text.lower()
    for keyword, title in REMINDER_TITLES.items():
        if keyword in lowered:
            return title
    return "Recordatorio de viaje"


def parse_reminder_entry(text: str) -> Optional[dict]:
    due_time = _extract_due_time(text)
    if not due_time:
        return None

    title = _extract_reminder_title(text)
    note = text.strip()
    return {"title": title, "due_time": due_time, "note": note}


def format_expense_summary(summary: dict) -> str:
    lines = [f"Total: {summary['total']:.2f}€", f"Gastos registrados: {summary['count']}"]
    for category, amount in summary["by_category"].items():
        lines.append(f"- {category}: {amount:.2f}€")
    return "\n".join(lines)
