from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SavingsGoal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    target_amount: float = Field(gt=0)
    current_amount: float = Field(default=0.0, ge=0)
    monthly_contribution: float = Field(default=0.0, ge=0)
    inflation_rate: float = Field(default=5.5)  # % EA Colombia reference
    profile_id: str = Field(default="default", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class SavingsGoalCreate(SQLModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    monthly_contribution: float = 0.0
    inflation_rate: float = 5.5
    profile_id: str = "default"


class SavingsGoalUpdate(SQLModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    monthly_contribution: Optional[float] = None
    inflation_rate: Optional[float] = None


class SavingsGoalRead(SQLModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    monthly_contribution: float
    inflation_rate: float
    profile_id: str
    created_at: datetime
    completed_at: Optional[datetime]
