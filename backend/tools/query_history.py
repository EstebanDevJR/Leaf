from langchain_core.tools import tool
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def query_history(
    limit: int = 10,
    category: str = None,
    transaction_type: str = None,
) -> str:
    """Consulta el historial de transacciones recientes.

    Args:
        limit: Número máximo de transacciones a retornar (máximo 50).
        category: Filtrar por categoría, por ejemplo "comida" (opcional).
        transaction_type: Filtrar por tipo: "expense" para gastos, "income" para ingresos (opcional).
    """
    query = select(Transaction).order_by(Transaction.date.desc()).limit(min(limit, 50))

    if category:
        query = query.where(Transaction.category == category)

    if transaction_type:
        try:
            tx_type = TransactionType(transaction_type)
            query = query.where(Transaction.type == tx_type)
        except ValueError:
            pass

    with Session(engine) as session:
        transactions = session.exec(query).all()

    if not transactions:
        return "No se encontraron transacciones."

    lines = []
    for tx in transactions:
        emoji = "💸" if tx.type == TransactionType.expense else "💰"
        date_str = tx.date.strftime("%d/%m")
        merchant = f" · {tx.merchant}" if tx.merchant else ""
        lines.append(
            f"{emoji} [{tx.id}] {date_str} | ${tx.amount:,.0f} | {tx.category} | {tx.description}{merchant}"
        )

    total_expenses = sum(t.amount for t in transactions if t.type == TransactionType.expense)
    total_income = sum(t.amount for t in transactions if t.type == TransactionType.income)

    summary = "\n".join(lines)
    if total_expenses > 0:
        summary += f"\n\nTotal gastos: ${total_expenses:,.0f}"
    if total_income > 0:
        summary += f"\nTotal ingresos: ${total_income:,.0f}"

    return summary
