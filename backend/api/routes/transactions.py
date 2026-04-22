from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.db.database import get_session
from backend.models.transaction import (
    Transaction,
    TransactionCreate,
    TransactionRead,
    TransactionType,
    TransactionUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    limit: int = 50,
    type: Optional[TransactionType] = None,
    category: Optional[str] = None,
    session: Session = Depends(get_session),
) -> list[Transaction]:
    query = select(Transaction).order_by(Transaction.date.desc()).limit(limit)
    if type:
        query = query.where(Transaction.type == type)
    if category:
        query = query.where(Transaction.category == category)
    return list(session.exec(query).all())


@router.get("/stats")
def get_stats(session: Session = Depends(get_session)) -> dict:
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    transactions = list(
        session.exec(select(Transaction).where(Transaction.date >= start_of_month)).all()
    )

    total_income = sum(t.amount for t in transactions if t.type == TransactionType.income)
    total_expenses = sum(t.amount for t in transactions if t.type == TransactionType.expense)

    by_category: dict[str, float] = {}
    for t in transactions:
        if t.type == TransactionType.expense:
            by_category[t.category] = by_category.get(t.category, 0) + t.amount

    return {
        "month": start_of_month.strftime("%B %Y"),
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses,
        "transaction_count": len(transactions),
        "expenses_by_category": by_category,
    }


@router.post("/", response_model=TransactionRead)
def create_transaction(
    tx: TransactionCreate,
    session: Session = Depends(get_session),
) -> Transaction:
    transaction = Transaction(**tx.model_dump())
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    updates: TransactionUpdate,
    session: Session = Depends(get_session),
) -> Transaction:
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    data = updates.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(tx, field, value)

    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
) -> dict:
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    session.delete(tx)
    session.commit()
    return {"ok": True}
