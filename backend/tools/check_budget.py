import calendar
from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.budget import Budget
from backend.models.transaction import Transaction, TransactionType


@tool
def check_budget(category: str = "all") -> str:
    """Verifica el presupuesto mensual actual para una categoría o para todas.

    Args:
        category: Categoría a verificar. Usa "all" para ver todas las categorías.
    """
    now = date.today()
    month_start = date(now.year, now.month, 1)

    with Session(engine) as session:
        if category == "all":
            budgets = session.exec(select(Budget)).all()
        else:
            budgets = session.exec(
                select(Budget).where(Budget.category == category)
            ).all()

        if not budgets:
            msg = "ninguna categoría" if category == "all" else category
            return (
                f"No hay presupuesto configurado para {msg}. "
                "Usa set_budget para configurar uno."
            )

        results = []
        for b in budgets:
            spent = (
                session.exec(
                    select(func.sum(Transaction.amount))
                    .where(Transaction.type == TransactionType.expense)
                    .where(Transaction.category == b.category)
                    .where(Transaction.date >= str(month_start))
                ).one()
                or 0
            )
            pct = (spent / b.monthly_limit * 100) if b.monthly_limit > 0 else 0
            status = (
                "🔴 EXCEDIDO" if pct > 100 else "🟡 ALERTA" if pct > 80 else "🟢 OK"
            )
            results.append(
                f"  {b.category}: ${spent:,.0f} / ${b.monthly_limit:,.0f} "
                f"({pct:.0f}%) {status}"
            )

    days_in_month = calendar.monthrange(now.year, now.month)[1]
    header = f"Presupuestos {now.strftime('%B %Y')} (día {now.day}/{days_in_month}):"
    return header + "\n" + "\n".join(results)
