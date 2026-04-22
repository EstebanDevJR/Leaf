from datetime import date, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType

DISCLAIMER = (
    "\n\n⚠️ Esta es información educativa, no asesoría de inversión. "
    "Consulta un asesor certificado para decisiones financieras."
)


@tool
def find_idle_money(threshold: float = 500_000, idle_days: int = 30) -> str:
    """Detecta si tienes dinero acumulado sin actividad reciente que podría estar generando rendimiento.

    Args:
        threshold: Saldo mínimo para considerar "dinero inactivo" (default 500,000 COP).
        idle_days: Días sin movimiento para considerar inactividad (default 30).
    """
    today = date.today()
    recent_start = today - timedelta(days=idle_days)

    with Session(engine) as session:
        total_income = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.income)
            ).one()
            or 0
        )
        total_expenses = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.expense)
            ).one()
            or 0
        )
        running_balance = total_income - total_expenses

        recent_count = (
            session.exec(
                select(func.count(Transaction.id))
                .where(Transaction.date >= str(recent_start))
            ).one()
            or 0
        )

    if running_balance <= 0:
        return "Tu balance acumulado es negativo o cero — no hay dinero inactivo que identificar."

    if running_balance < threshold:
        return (
            f"Balance acumulado: ${running_balance:,.0f}\n"
            f"Está por debajo del umbral de ${threshold:,.0f} — no se considera dinero inactivo."
        )

    lines = [f"💤 Dinero inactivo detectado:\n"]
    lines.append(f"  Balance acumulado (ingresos − gastos): ${running_balance:,.0f}")
    lines.append(f"  Movimientos en los últimos {idle_days} días: {recent_count}")

    if recent_count < 5:
        lines.append(f"\n  ⚠️ Baja actividad financiera reciente.")

    # CDT projection at reference rate (11.5% EA)
    ref_rate = 0.115
    rendimiento_anual = running_balance * ref_rate
    rendimiento_12m = rendimiento_anual
    rendimiento_6m = running_balance * ref_rate * 0.5

    lines.append(f"\n  Si lo pones a trabajar en un CDT (referencia ~11.5% EA):")
    lines.append(f"    • 6 meses: +${rendimiento_6m:,.0f}")
    lines.append(f"    • 12 meses: +${rendimiento_12m:,.0f}")
    lines.append("\n  Otras opciones: cuenta de ahorros de alta rentabilidad, fiducia.")
    lines.append(DISCLAIMER)

    return "\n".join(lines)
