"""Agente Investigador Financiero — monitoreo autónomo con toggle ON/OFF."""

import logging
from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.alert import Alert
from backend.models.investigador_config import InvestigadorConfig
from backend.tools.detect_anomaly import detect_anomaly
from backend.tools.find_idle_money import find_idle_money

logger = logging.getLogger(__name__)

INVESTIGADOR_TOOLS = [
    # imported here for use by the orchestrator
]

# Lazy import to avoid circular imports at module load time
def _get_investigador_tools():
    from backend.tools.analyze_patterns import analyze_patterns
    from backend.tools.analyze_weekday import analyze_weekday
    from backend.tools.calculate_savings_goal import calculate_savings_goal
    from backend.tools.detect_anomaly import detect_anomaly
    from backend.tools.emergency_fund_status import emergency_fund_status
    from backend.tools.explain_concept import explain_concept
    from backend.tools.find_idle_money import find_idle_money
    from backend.tools.find_subscriptions import find_subscriptions
    from backend.tools.generate_insight_report import generate_insight_report
    from backend.tools.get_cdt_rates import get_cdt_rates
    return [
        analyze_patterns, detect_anomaly, find_subscriptions, calculate_savings_goal,
        get_cdt_rates, analyze_weekday, find_idle_money, emergency_fund_status,
        generate_insight_report, explain_concept,
    ]


class TriggerType(str, Enum):
    NUEVA_TX = "nueva_tx"
    SCHEDULER = "scheduler"
    FIN_DE_MES = "fin_de_mes"
    USUARIO_PIDE = "usuario_pide"


class InvestigadorState(BaseModel):
    trigger: TriggerType = TriggerType.SCHEDULER
    user_id: str = "local"
    enabled: bool = True
    anomalias: list[str] = []
    insights: list[str] = []
    alertas: list[str] = []
    debe_notificar: bool = False


def _is_enabled(user_id: str) -> bool:
    with Session(engine) as session:
        config = session.exec(
            select(InvestigadorConfig).where(InvestigadorConfig.user_id == user_id)
        ).first()
        if config is None:
            # Default: enabled
            return True
        return config.enabled


def _check_enabled(state: InvestigadorState) -> str:
    if not _is_enabled(state.user_id):
        logger.debug("Investigador OFF para user=%s — saltando análisis", state.user_id)
        return "fin"
    return "analizar"


def _analizar(state: InvestigadorState) -> InvestigadorState:
    """Detecta anomalías de gasto."""
    anomalias = []
    try:
        result = detect_anomaly.invoke({"category": "all"})
        if "🚨" in result:
            anomalias.append(result)
    except Exception as e:
        logger.warning("detect_anomaly failed: %s", e)

    return InvestigadorState(
        **{**state.model_dump(), "anomalias": anomalias}
    )


def _idle_money(state: InvestigadorState) -> InvestigadorState:
    """Detecta dinero inactivo."""
    insights = list(state.insights)
    try:
        result = find_idle_money.invoke({"threshold": 500_000, "idle_days": 30})
        if "💤" in result:
            insights.append(result)
    except Exception as e:
        logger.warning("find_idle_money failed: %s", e)

    debe_notificar = bool(state.anomalias) or bool(insights)
    return InvestigadorState(
        **{**state.model_dump(), "insights": insights, "debe_notificar": debe_notificar}
    )


def _notificar(state: InvestigadorState) -> InvestigadorState:
    """Persiste hallazgos como alertas en la BD y envía notificaciones push."""
    alertas_creadas = []
    push_lines = []

    with Session(engine) as session:
        for anomalia in state.anomalias:
            alert = Alert(
                type="investigador_anomalia",
                severity="warn",
                message="Anomalía de gasto detectada",
                detail=anomalia[:2000],
            )
            session.add(alert)
            alertas_creadas.append("anomalía")
            push_lines.append(f"⚠️ {anomalia[:200]}")
            logger.info("Alerta investigador: anomalía creada")

        for insight in state.insights:
            alert = Alert(
                type="investigador_idle_money",
                severity="info",
                message="Dinero inactivo detectado",
                detail=insight[:2000],
            )
            session.add(alert)
            alertas_creadas.append("dinero inactivo")
            push_lines.append(f"💤 {insight[:200]}")
            logger.info("Alerta investigador: dinero inactivo creada")

        session.commit()

    # Push notifications via Telegram
    if push_lines:
        try:
            import asyncio
            from backend.services.telegram_bot import send_notification
            msg = "🌿 Leaf — Investigador\n\n" + "\n\n".join(push_lines)
            asyncio.create_task(send_notification(msg))
        except Exception as e:
            logger.debug("Telegram push failed: %s", e)

    return InvestigadorState(**{**state.model_dump(), "alertas": alertas_creadas})


# ── Build graph ──────────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(InvestigadorState)

    g.add_node("analizar", _analizar)
    g.add_node("idle_money", _idle_money)
    g.add_node("notificar", _notificar)
    g.add_node("fin", lambda s: s)

    g.add_conditional_edges(START, _check_enabled, {"analizar": "analizar", "fin": "fin"})
    g.add_edge("analizar", "idle_money")
    g.add_conditional_edges(
        "idle_money",
        lambda s: "notificar" if s.debe_notificar else "fin",
        {"notificar": "notificar", "fin": "fin"},
    )
    g.add_edge("notificar", "fin")
    g.add_edge("fin", END)

    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def run_investigador(
    trigger: TriggerType = TriggerType.SCHEDULER,
    user_id: str = "local",
) -> InvestigadorState:
    """Ejecuta el grafo del investigador con el trigger dado."""
    initial = InvestigadorState(trigger=trigger, user_id=user_id)
    result = get_graph().invoke(initial)
    return InvestigadorState(**result) if isinstance(result, dict) else result
