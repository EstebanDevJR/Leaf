from datetime import datetime

from sqlmodel import Field, SQLModel


class Budget(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    category: str = Field(index=True, unique=True)
    monthly_limit: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BudgetCreate(SQLModel):
    category: str
    monthly_limit: float


class BudgetRead(SQLModel):
    id: int
    category: str
    monthly_limit: float
    created_at: datetime
    updated_at: datetime
