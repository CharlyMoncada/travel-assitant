import datetime
from datetime import timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from .db import Base, SessionLocal


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    note = Column(Text, nullable=True)
    due_time = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc))


def save_reminder(title: str, due_time: str, note: str):
    with SessionLocal() as session:
        reminder = Reminder(title=title, due_time=due_time, note=note)
        session.add(reminder)
        session.commit()
        session.refresh(reminder)
        return {
            "id": reminder.id,
            "title": reminder.title,
            "due_time": reminder.due_time,
            "note": reminder.note,
            "created_at": reminder.created_at.isoformat(),
        }


def list_reminders(date_filter: str = None):
    """
    Retorna todos los recordatorios ordenados por due_time ascendente.
    Si se proporciona date_filter (formato: YYYY-MM-DD), retorna solo los recordatorios
    cuyo due_time comience con ese prefijo de fecha.
    """
    with SessionLocal() as session:
        query = session.query(Reminder)
        if date_filter:
            query = query.filter(Reminder.due_time.like(f"{date_filter}%"))
        return [
            {
                "id": reminder.id,
                "title": reminder.title,
                "due_time": reminder.due_time,
                "note": reminder.note,
            }
            for reminder in query.order_by(Reminder.due_time.asc()).all()
        ]


def modify_reminder(reminder_id: int, title: str = None, due_time: str = None, note: str = None) -> dict:
    with SessionLocal() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return {"error": f"Reminder with ID {reminder_id} not found in database"}
        
        if title is not None:
            reminder.title = title
        if due_time is not None:
            reminder.due_time = due_time
        if note is not None:
            reminder.note = note
            
        session.commit()
        session.refresh(reminder)
        return {
            "success": True,
            "message": f"Reminder with ID {reminder_id} modified successfully",
            "reminder": {
                "id": reminder.id,
                "title": reminder.title,
                "due_time": reminder.due_time,
                "note": reminder.note,
                "created_at": reminder.created_at.isoformat(),
            }
        }


def delete_reminder(reminder_id: int) -> dict:
    with SessionLocal() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return {"error": f"Reminder with ID {reminder_id} not found in database"}
        
        session.delete(reminder)
        session.commit()
        return {
            "success": True,
            "message": f"Reminder with ID {reminder_id} deleted successfully from database"
        }
