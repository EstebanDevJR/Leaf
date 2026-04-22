"""Rutas del Agente Investigador — toggle, estado y trigger manual."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.agents.investigador import TriggerType, run_investigador
from backend.db.database import engine
from backend.models.investigador_config import InvestigadorConfig, InvestigadorConfigRead

router = APIRouter()


def _get_or_create_config(session: Session, user_id: str = "local") -> InvestigadorConfig:
    config = session.exec(
        select(InvestigadorConfig).where(InvestigadorConfig.user_id == user_id)
    ).first()
    if config is None:
        config = InvestigadorConfig(user_id=user_id, enabled=True)
        session.add(config)
        session.commit()
        session.refresh(config)
    return config


@router.get("/status", response_model=InvestigadorConfigRead)
def get_status(user_id: str = "local"):
    """Devuelve el estado actual del toggle del Investigador."""
    with Session(engine) as session:
        config = _get_or_create_config(session, user_id)
        return InvestigadorConfigRead(
            user_id=config.user_id,
            enabled=config.enabled,
            updated_at=config.updated_at,
        )


class ToggleBody(BaseModel):
    enabled: bool


@router.post("/toggle", response_model=InvestigadorConfigRead)
def toggle(body: ToggleBody, user_id: str = "local"):
    """Activa o desactiva el Agente Investigador."""
    with Session(engine) as session:
        config = _get_or_create_config(session, user_id)
        config.enabled = body.enabled
        config.updated_at = datetime.utcnow()
        session.add(config)
        session.commit()
        session.refresh(config)
        return InvestigadorConfigRead(
            user_id=config.user_id,
            enabled=config.enabled,
            updated_at=config.updated_at,
        )


class RunBody(BaseModel):
    trigger: TriggerType = TriggerType.USUARIO_PIDE
    user_id: str = "local"


class RunResult(BaseModel):
    anomalias: list[str]
    insights: list[str]
    alertas: list[str]
    debe_notificar: bool


@router.post("/run", response_model=RunResult)
def run_manual(body: RunBody):
    """Dispara el Investigador manualmente y retorna los hallazgos."""
    try:
        result = run_investigador(trigger=body.trigger, user_id=body.user_id)
        return RunResult(
            anomalias=result.anomalias,
            insights=result.insights,
            alertas=result.alertas,
            debe_notificar=result.debe_notificar,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
