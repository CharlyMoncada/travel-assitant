import datetime
from datetime import timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from .db import Base, SessionLocal


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc))


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
                    "id": item.id,
                    "description": item.description,
                    "amount": item.amount,
                    "category": item.category,
                    "created_at": item.created_at.isoformat(),
                }
                for item in expenses
            ]
        }


def modify_expense(expense_id: int, description: str = None, amount: float = None, category: str = None) -> dict:
    with SessionLocal() as session:
        expense = session.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            return {"error": f"Expense with ID {expense_id} not found in database"}
        
        if description is not None:
            expense.description = description
        if amount is not None:
            expense.amount = amount
        if category is not None:
            expense.category = category
            
        session.commit()
        session.refresh(expense)
        return {
            "success": True,
            "message": f"Expense with ID {expense_id} modified successfully",
            "expense": {
                "id": expense.id,
                "description": expense.description,
                "amount": expense.amount,
                "category": expense.category,
                "created_at": expense.created_at.isoformat(),
            }
        }


def delete_expense(expense_id: int) -> dict:
    with SessionLocal() as session:
        expense = session.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            return {"error": f"Expense with ID {expense_id} not found in database"}
        
        session.delete(expense)
        session.commit()
        return {
            "success": True,
            "message": f"Expense with ID {expense_id} deleted successfully from database"
        }
