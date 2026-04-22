from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.budget import Budget, BudgetCreate, BudgetRead

router = APIRouter()


@router.get("/", response_model=list[BudgetRead])
def list_budgets():
    with Session(engine) as session:
        return session.exec(select(Budget).order_by(Budget.category)).all()


@router.put("/{category}", response_model=BudgetRead)
def upsert_budget(category: str, data: BudgetCreate):
    with Session(engine) as session:
        existing = session.exec(
            select(Budget).where(Budget.category == category)
        ).first()
        if existing:
            existing.monthly_limit = data.monthly_limit
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        budget = Budget(category=category, monthly_limit=data.monthly_limit)
        session.add(budget)
        session.commit()
        session.refresh(budget)
        return budget


@router.delete("/{category}", status_code=204)
def delete_budget(category: str):
    with Session(engine) as session:
        budget = session.exec(
            select(Budget).where(Budget.category == category)
        ).first()
        if not budget:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        session.delete(budget)
        session.commit()
