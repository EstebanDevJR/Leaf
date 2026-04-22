import csv
import io
from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.transaction import Transaction


@tool
def generate_report(month: str = "current", format: str = "summary") -> str:
    """Genera un reporte de transacciones del mes en texto o CSV.

    Args:
        month: Mes en formato YYYY-MM o "current" para el mes actual.
        format: "summary" para resumen legible, "csv" para datos tabulares.
    """
    now = date.today()
    if month == "current":
        year, m = now.year, now.month
    else:
        try:
            year, m = (int(p) for p in month.split("-"))
        except ValueError:
            return "Formato inválido. Usa YYYY-MM o 'current'."

    month_start = date(year, m, 1)
    month_end = date(year + 1, 1, 1) if m == 12 else date(year, m + 1, 1)

    with Session(engine) as session:
        txs = session.exec(
            select(Transaction)
            .where(Transaction.date >= str(month_start))
            .where(Transaction.date < str(month_end))
            .order_by(Transaction.date)
        ).all()

    if not txs:
        return f"No hay transacciones en {month_start.strftime('%B %Y')}."

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Fecha", "Tipo", "Categoría", "Descripción", "Comercio", "Monto"])
        for tx in txs:
            writer.writerow([
                tx.id, tx.date, tx.type, tx.category,
                tx.description, tx.merchant or "", tx.amount,
            ])
        return (
            f"CSV generado — {len(txs)} transacciones ({month_start.strftime('%B %Y')}):\n"
            f"```csv\n{output.getvalue()}```"
        )

    # Human-readable summary
    incomes = [t for t in txs if t.type == "income"]
    expenses = [t for t in txs if t.type == "expense"]
    total_in = sum(t.amount for t in incomes)
    total_ex = sum(t.amount for t in expenses)

    lines = [
        f"📊 Reporte {month_start.strftime('%B %Y')} — {len(txs)} transacciones\n",
        f"  Ingresos ({len(incomes)}):  ${total_in:,.0f}",
        f"  Gastos   ({len(expenses)}): ${total_ex:,.0f}",
        f"  Balance:          ${'+'if total_in >= total_ex else ''}{total_in - total_ex:,.0f}\n",
        "Detalle:",
    ]
    for tx in txs:
        sign = "+" if tx.type == "income" else "−"
        lines.append(
            f"  {tx.date}  {sign}${tx.amount:,.0f}  {tx.category}  {tx.description}"
        )
    return "\n".join(lines)
