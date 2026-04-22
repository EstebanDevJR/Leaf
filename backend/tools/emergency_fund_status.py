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
def emergency_fund_status(target_months: int = 3) -> str:
    """Calcula cuántos meses de gastos cubre tu balance acumulado y qué falta para el fondo de emergencia.

    Args:
        target_months: Meta de meses de gastos en fondo de emergencia (default 3).
    """
    today = date.today()
    three_months_ago = today - timedelta(days=90)

    with Session(engine) as session:
        total_income = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.income)
            ).one()
            or 0
        )
        total_expenses_all = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.expense)
            ).one()
            or 0
        )
        recent_expenses = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.expense)
                .where(Transaction.date >= str(three_months_ago))
            ).one()
            or 0
        )

    balance = total_income - total_expenses_all
    avg_monthly_expenses = recent_expenses / 3 if recent_expenses > 0 else 0

    if avg_monthly_expenses <= 0:
        return "Sin gastos registrados en los últimos 3 meses para calcular el fondo de emergencia."

    months_covered = balance / avg_monthly_expenses if balance > 0 else 0
    target_amount = avg_monthly_expenses * target_months
    gap = target_amount - balance

    lines = [f"🛡️ Fondo de emergencia:\n"]
    lines.append(f"  Balance disponible:       ${balance:,.0f}")
    lines.append(f"  Gastos promedio/mes:      ${avg_monthly_expenses:,.0f}")
    lines.append(f"  Cobertura actual:         {months_covered:.1f} meses")
    lines.append(f"  Meta ({target_months} meses):            ${target_amount:,.0f}")

    if months_covered >= target_months:
        lines.append(f"\n  ✅ Ya tienes tu fondo de emergencia completo.")
        surplus = balance - target_amount
        if surplus > 500_000:
            lines.append(
                f"  Tienes ${surplus:,.0f} por encima de la meta — "
                f"considera invertirlos (CDT, fiducia)."
            )
    else:
        lines.append(f"\n  ❌ Te faltan ${gap:,.0f} para completar {target_months} meses.")

        # Project how many months to complete it at current savings rate
        month_start = today - timedelta(days=30)
        with Session(engine) as session:
            inc_30 = (
                session.exec(
                    select(func.sum(Transaction.amount))
                    .where(Transaction.type == TransactionType.income)
                    .where(Transaction.date >= str(month_start))
                ).one()
                or 0
            )
            exp_30 = (
                session.exec(
                    select(func.sum(Transaction.amount))
                    .where(Transaction.type == TransactionType.expense)
                    .where(Transaction.date >= str(month_start))
                ).one()
                or 0
            )
        monthly_savings = inc_30 - exp_30
        if monthly_savings > 0:
            months_to_goal = gap / monthly_savings
            lines.append(
                f"  A tu ritmo actual (${monthly_savings:,.0f}/mes), "
                f"lo lograrías en {months_to_goal:.1f} meses."
            )
        else:
            lines.append("  Registra ingresos para proyectar cuándo completarás el fondo.")

    lines.append(DISCLAIMER)
    return "\n".join(lines)
