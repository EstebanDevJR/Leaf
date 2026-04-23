from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: str = Field(index=True, unique=True)
    name: str
    color: str = Field(default="#22c55e")  # green default
    monthly_income: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfileCreate(SQLModel):
    profile_id: str
    name: str
    color: str = "#22c55e"
    monthly_income: float = 0.0


class UserProfileRead(SQLModel):
    id: int
    profile_id: str
    name: str
    color: str
    monthly_income: float
    created_at: datetime
