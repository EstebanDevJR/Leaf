from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.alert import Alert, AlertRead

router = APIRouter()


@router.get("/", response_model=list[AlertRead])
def list_alerts(include_dismissed: bool = False):
    """Returns all alerts, optionally including dismissed ones."""
    with Session(engine) as session:
        q = select(Alert).order_by(Alert.triggered_at.desc())
        if not include_dismissed:
            q = q.where(Alert.dismissed_at.is_(None))
        alerts = session.exec(q).all()
        return [
            AlertRead(
                id=a.id,
                type=a.type,
                severity=a.severity,
                message=a.message,
                detail=a.detail,
                triggered_at=a.triggered_at,
                dismissed=a.dismissed,
            )
            for a in alerts
        ]


@router.post("/{alert_id}/dismiss", status_code=204)
def dismiss_alert(alert_id: int):
    with Session(engine) as session:
        alert = session.get(Alert, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")
        alert.dismissed_at = datetime.utcnow()
        session.add(alert)
        session.commit()


@router.delete("/dismissed", status_code=204)
def clear_dismissed():
    """Removes all dismissed alerts."""
    with Session(engine) as session:
        alerts = session.exec(
            select(Alert).where(Alert.dismissed_at.is_not(None))
        ).all()
        for a in alerts:
            session.delete(a)
        session.commit()
