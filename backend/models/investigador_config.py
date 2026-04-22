from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class InvestigadorConfig(SQLModel, table=True):
    """Toggle y configuración del Agente Investigador por usuario."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="local", index=True, unique=True)
    enabled: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InvestigadorConfigRead(SQLModel):
    user_id: str
    enabled: bool
    updated_at: datetime
