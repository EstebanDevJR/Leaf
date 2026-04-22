from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.budget import Budget
from backend.models.transaction import Transaction, TransactionType


@tool
def summarize_month(month: str = "current") -> str:
    """Genera un resumen financiero completo: ingresos, gastos, balance, presupuestos y top categorías.

    Args:
        month: Mes en formato YYYY-MM o "current" para el mes actual.
    """
    now = date.today()
    if month == "current":
        year, m = now.year, now.month
    else:
        try:
            year, m = (int(p) for p in month.split("-"))
        except ValueError:
            return "Formato de mes inválido. Usa YYYY-MM o 'current'."

    month_start = date(year, m, 1)
    month_end = date(year + 1, 1, 1) if m == 12 else date(year, m + 1, 1)

    with Session(engine) as session:
        total_income = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.income)
                .where(Transaction.date >= str(month_start))
                .where(Transaction.date < str(month_end))
            ).one()
            or 0
        )

        expense_rows = session.exec(
            select(Transaction.category, func.sum(Transaction.amount).label("total"))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= str(month_start))
            .where(Transaction.date < str(month_end))
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
        ).all()

        total_expenses = sum(r[1] for r in expense_rows)
        balance = total_income - total_expenses

        budgets = {
            b.category: b.monthly_limit
            for b in session.exec(select(Budget)).all()
        }

        tx_count = (
            session.exec(
                select(func.count(Transaction.id))
                .where(Transaction.date >= str(month_start))
                .where(Transaction.date < str(month_end))
            ).one()
            or 0
        )

    lines = [
        f"📅 Resumen {month_start.strftime('%B %Y')}:",
        f"  💼 Ingresos:      ${total_income:,.0f}",
        f"  💸 Gastos:        ${total_expenses:,.0f}",
        f"  📊 Balance:       {'+'if balance >= 0 else ''}{balance:,.0f}",
        f"  🧾 Transacciones: {tx_count}",
        "",
        "Gastos por categoría:",
    ]

    for cat, total in expense_rows[:6]:
        limit = budgets.get(cat)
        if limit:
            pct = total / limit * 100
            flag = " 🔴" if pct > 100 else " 🟡" if pct > 80 else ""
            lines.append(
                f"  {cat}: ${total:,.0f} / ${limit:,.0f} ({pct:.0f}%){flag}"
            )
        else:
            lines.append(f"  {cat}: ${total:,.0f}")

    if total_income > 0:
        spend_ratio = total_expenses / total_income * 100
        lines.append(f"\nUsaste el {spend_ratio:.0f}% de tus ingresos este mes.")

    return "\n".join(lines)
