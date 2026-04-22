from langchain_core.tools import tool
from sqlmodel import Session

from backend.db.database import engine
from backend.models.transaction import Transaction


@tool
def delete_transaction(transaction_id: int) -> str:
    """Elimina una transacción por su ID.

    Args:
        transaction_id: ID de la transacción a eliminar.
    """
    with Session(engine) as session:
        tx = session.get(Transaction, transaction_id)
        if not tx:
            return f"No se encontró una transacción con ID {transaction_id}."

        description = tx.description
        amount = tx.amount
        session.delete(tx)
        session.commit()

    return f"Transacción {transaction_id} eliminada ✓ — {description} (${amount:,.0f})"
