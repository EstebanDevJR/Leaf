from datetime import datetime

from sqlmodel import Field, SQLModel


class Alert(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: str  # deadline | threshold | gmf_monthly | retention
    severity: str = "info"  # info | warn | urgent
    message: str
    detail: str = ""
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    dismissed_at: datetime | None = None

    @property
    def dismissed(self) -> bool:
        return self.dismissed_at is not None


class AlertRead(SQLModel):
    id: int
    type: str
    severity: str
    message: str
    detail: str
    triggered_at: datetime
    dismissed: bool
