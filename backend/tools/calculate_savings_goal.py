from datetime import date, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def calculate_savings_goal(goal_amount: float, monthly_savings: float = 0) -> str:
    """Proyecta cuándo alcanzarás una meta de ahorro dado un monto objetivo.

    Args:
        goal_amount: Monto objetivo en COP.
        monthly_savings: Ahorro mensual estimado. Si es 0, se calcula del historial.
    """
    today = date.today()

    if monthly_savings <= 0:
        # Calculate from last 3 months income - expenses
        start = today - timedelta(days=90)
        with Session(engine) as session:
            total_income = (
                session.exec(
                    select(func.sum(Transaction.amount))
                    .where(Transaction.type == TransactionType.income)
                    .where(Transaction.date >= str(start))
                ).one()
                or 0
            )
            total_expenses = (
                session.exec(
                    select(func.sum(Transaction.amount))
                    .where(Transaction.type == TransactionType.expense)
                    .where(Transaction.date >= str(start))
                ).one()
                or 0
            )
        monthly_savings = (total_income - total_expenses) / 3

    if monthly_savings <= 0:
        return (
            "⚠️ Tu ahorro mensual estimado es negativo o cero.\n"
            "Registra tus ingresos o indica un monto de ahorro mensual para proyectar la meta."
        )

    months_needed = goal_amount / monthly_savings
    target_date = today + timedelta(days=int(months_needed * 30.5))
    years = int(months_needed // 12)
    remaining_months = int(months_needed % 12)

    time_str = ""
    if years > 0:
        time_str += f"{years} año{'s' if years > 1 else ''}"
    if remaining_months > 0:
        time_str += f"{' y ' if years > 0 else ''}{remaining_months} mes{'es' if remaining_months > 1 else ''}"

    lines = [
        f"🎯 Meta de ahorro: ${goal_amount:,.0f}",
        f"  Ahorro mensual: ${monthly_savings:,.0f}",
        f"  Tiempo estimado: {time_str} ({months_needed:.1f} meses)",
        f"  Fecha estimada: {target_date.strftime('%B %Y')}",
    ]

    # Show impact of boosting savings
    for boost in (0.1, 0.25):
        boosted = monthly_savings * (1 + boost)
        boosted_months = goal_amount / boosted
        saved_months = months_needed - boosted_months
        lines.append(
            f"\n  Si ahorras {boost*100:.0f}% más (${boosted:,.0f}/mes): "
            f"{boosted_months:.1f} meses — llegas {saved_months:.1f} meses antes"
        )

    return "\n".join(lines)
