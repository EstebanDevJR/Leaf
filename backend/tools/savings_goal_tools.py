"""Tools para metas de ahorro inteligentes con proyecciones ajustadas por inflación."""

from datetime import date, datetime, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.savings_goal import SavingsGoal


def _months_to_goal(target: float, current: float, monthly: float, inflation_pct: float) -> float:
    """Calcula meses para alcanzar la meta con inflación compuesta mensual."""
    if monthly <= 0:
        return float("inf")
    monthly_inflation = (1 + inflation_pct / 100) ** (1 / 12) - 1
    # Real target grows with inflation each month
    balance = current
    real_target = target
    months = 0
    while balance < real_target and months < 600:
        balance += monthly
        real_target *= 1 + monthly_inflation
        months += 1
    return months


@tool
def create_savings_goal(
    name: str,
    target_amount: float,
    monthly_contribution: float,
    current_amount: float = 0.0,
    inflation_rate: float = 5.5,
    profile_id: str = "default",
) -> str:
    """Crea una nueva meta de ahorro con proyección ajustada por inflación.

    Args:
        name: Nombre de la meta (ej: 'Fondo viaje', 'Carro').
        target_amount: Monto objetivo en COP.
        monthly_contribution: Cuánto ahorrarás por mes en COP.
        current_amount: Lo que ya tienes ahorrado (default 0).
        inflation_rate: Tasa de inflación anual estimada % (default 5.5% Colombia).
        profile_id: Perfil al que pertenece la meta.
    """
    with Session(engine) as session:
        goal = SavingsGoal(
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            monthly_contribution=monthly_contribution,
            inflation_rate=inflation_rate,
            profile_id=profile_id,
        )
        session.add(goal)
        session.commit()
        session.refresh(goal)

    months = _months_to_goal(target_amount, current_amount, monthly_contribution, inflation_rate)
    if months == float("inf"):
        return f"Meta '{name}' creada (ID {goal.id}). Necesitas definir una contribución mensual para proyectar."

    target_date = date.today() + timedelta(days=int(months * 30.5))
    return (
        f"✅ Meta '{name}' creada (ID {goal.id})\n"
        f"  Objetivo: ${target_amount:,.0f}\n"
        f"  Ya ahorrado: ${current_amount:,.0f}\n"
        f"  Ahorro mensual: ${monthly_contribution:,.0f}\n"
        f"  Inflación estimada: {inflation_rate}% EA\n"
        f"  Meta ajustada: ~${target_amount * (1 + inflation_rate/100) ** (months/12):,.0f}\n"
        f"  Lo logras en: {months} meses ({target_date.strftime('%B %Y')})"
    )


@tool
def list_savings_goals(profile_id: str = "default") -> str:
    """Lista todas las metas de ahorro activas con su progreso y proyección.

    Args:
        profile_id: Perfil del que listar metas.
    """
    with Session(engine) as session:
        goals = session.exec(
            select(SavingsGoal)
            .where(SavingsGoal.profile_id == profile_id)
            .where(SavingsGoal.completed_at.is_(None))
        ).all()

    if not goals:
        return "No tienes metas de ahorro activas. Crea una con create_savings_goal."

    lines = ["🎯 Metas de ahorro activas:\n"]
    for g in goals:
        progress_pct = g.current_amount / g.target_amount * 100 if g.target_amount > 0 else 0
        bar = "█" * int(progress_pct / 10) + "░" * (10 - int(progress_pct / 10))
        months = _months_to_goal(
            g.target_amount, g.current_amount, g.monthly_contribution, g.inflation_rate
        )
        eta = (
            f"{int(months)} meses"
            if months != float("inf")
            else "sin contribución definida"
        )
        lines.append(
            f"  [{g.id}] {g.name}\n"
            f"      {bar} {progress_pct:.0f}% — ${g.current_amount:,.0f} / ${g.target_amount:,.0f}\n"
            f"      ${g.monthly_contribution:,.0f}/mes · inflación {g.inflation_rate}% · ETA: {eta}"
        )
    return "\n".join(lines)


@tool
def update_savings_goal(goal_id: int, deposited_amount: float) -> str:
    """Registra un aporte a una meta de ahorro y recalcula la proyección.

    Args:
        goal_id: ID de la meta de ahorro.
        deposited_amount: Monto depositado en COP.
    """
    with Session(engine) as session:
        goal = session.get(SavingsGoal, goal_id)
        if not goal:
            return f"Meta {goal_id} no encontrada."

        goal.current_amount += deposited_amount
        goal.updated_at = datetime.utcnow()

        if goal.current_amount >= goal.target_amount:
            goal.completed_at = datetime.utcnow()
            session.add(goal)
            session.commit()
            return f"🎉 ¡Meta '{goal.name}' completada! Ahorraste ${goal.current_amount:,.0f}."

        session.add(goal)
        session.commit()
        session.refresh(goal)

    progress_pct = goal.current_amount / goal.target_amount * 100
    months = _months_to_goal(
        goal.target_amount, goal.current_amount, goal.monthly_contribution, goal.inflation_rate
    )
    eta = f"{int(months)} meses" if months != float("inf") else "sin contribución"
    return (
        f"✅ Aporte de ${deposited_amount:,.0f} registrado en '{goal.name}'\n"
        f"  Progreso: ${goal.current_amount:,.0f} / ${goal.target_amount:,.0f} ({progress_pct:.0f}%)\n"
        f"  ETA restante: {eta}"
    )


SAVINGS_GOAL_TOOLS = [create_savings_goal, list_savings_goals, update_savings_goal]
