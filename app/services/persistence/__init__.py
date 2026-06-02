"""Persistence package: re-export domain persistence functions for compatibility."""

from .db import init_db
from .expense_persistence import (
    save_expense,
    get_expense_summary,
    modify_expense,
    delete_expense,
)
from .reminder_persistence import (
    save_reminder,
    list_reminders,
    modify_reminder,
    delete_reminder,
)

__all__ = [
    "init_db",
    "save_expense",
    "get_expense_summary",
    "modify_expense",
    "delete_expense",
    "save_reminder",
    "list_reminders",
    "modify_reminder",
    "delete_reminder",
]
