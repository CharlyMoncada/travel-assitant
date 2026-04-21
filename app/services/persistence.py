import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///travel_assistant.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    note = Column(Text, nullable=True)
    due_time = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def save_expense(description: str, amount: float, category: str):
    with SessionLocal() as session:
        expense = Expense(description=description, amount=amount, category=category)
        session.add(expense)
        session.commit()
        session.refresh(expense)
        return {
            "id": expense.id,
            "description": expense.description,
            "amount": expense.amount,
            "category": expense.category,
            "created_at": expense.created_at.isoformat(),
        }


def get_expense_summary():
    with SessionLocal() as session:
        expenses = session.query(Expense).all()
        total = sum(item.amount for item in expenses)
        categories = {}
        for item in expenses:
            key = item.category or "otro"
            categories[key] = categories.get(key, 0.0) + item.amount
        return {
            "total": total,
            "count": len(expenses),
            "by_category": categories,
            "items": [
                {
                    "description": item.description,
                    "amount": item.amount,
                    "category": item.category,
                    "created_at": item.created_at.isoformat(),
                }
                for item in expenses
            ],
        }


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


def list_reminders():
    with SessionLocal() as session:
        return [
            {
                "id": reminder.id,
                "title": reminder.title,
                "due_time": reminder.due_time,
                "note": reminder.note,
            }
            for reminder in session.query(Reminder).order_by(Reminder.created_at.desc()).all()
        ]
