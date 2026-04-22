from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TransactionType(str, Enum):
    expense = "expense"
    income = "income"


EXPENSE_CATEGORIES = [
    "comida", "transporte", "vivienda", "salud",
    "entretenimiento", "ropa", "servicios", "otro",
]

INCOME_CATEGORIES = ["salario", "freelance", "ventas", "inversiones", "otro"]


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float = Field(gt=0)
    description: str
    category: str
    type: TransactionType
    merchant: Optional[str] = None
    date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class TransactionCreate(SQLModel):
    amount: float
    description: str
    category: str
    type: TransactionType
    merchant: Optional[str] = None
    notes: Optional[str] = None


class TransactionRead(SQLModel):
    id: int
    amount: float
    description: str
    category: str
    type: TransactionType
    merchant: Optional[str]
    date: datetime
    notes: Optional[str]


class TransactionUpdate(SQLModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    merchant: Optional[str] = None
    notes: Optional[str] = None
