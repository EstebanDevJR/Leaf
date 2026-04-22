import calendar
from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def predict_expenses(category: str = "all") -> str:
    """Predice los gastos del mes basándose en el ritmo de gasto hasta hoy.

    Args:
        category: Categoría a predecir. Usa "all" para el total general.
    """
    now = date.today()
    month_start = date(now.year, now.month, 1)
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_elapsed = (now - month_start).days + 1
    days_remaining = days_in_month - days_elapsed

    with Session(engine) as session:
        query = (
            select(func.sum(Transaction.amount))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= str(month_start))
        )
        if category != "all":
            query = query.where(Transaction.category == category)
        spent_so_far = session.exec(query).one() or 0

    daily_rate = spent_so_far / days_elapsed if days_elapsed > 0 else 0
    predicted_total = daily_rate * days_in_month
    expected_remaining = daily_rate * days_remaining
    label = category if category != "all" else "total"

    return (
        f"Proyección {label} ({now.strftime('%B %Y')}):\n"
        f"  Gastado hasta hoy (día {days_elapsed}): ${spent_so_far:,.0f}\n"
        f"  Ritmo diario: ${daily_rate:,.0f}/día\n"
        f"  Proyección al cierre (día {days_in_month}): ${predicted_total:,.0f}\n"
        f"  Se esperan ~${expected_remaining:,.0f} más en {days_remaining} días"
    )
