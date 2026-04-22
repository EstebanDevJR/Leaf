from langchain_core.tools import tool
from sqlmodel import Session

from backend.db.database import engine
from backend.models.transaction import Transaction


@tool
def edit_transaction(
    transaction_id: int,
    amount: float = None,
    description: str = None,
    category: str = None,
    merchant: str = None,
    notes: str = None,
) -> str:
    """Edita una transacción existente por su ID.

    Args:
        transaction_id: ID de la transacción a editar.
        amount: Nuevo monto en COP (opcional).
        description: Nueva descripción (opcional).
        category: Nueva categoría (opcional).
        merchant: Nuevo comercio/fuente (opcional).
        notes: Nuevas notas (opcional).
    """
    with Session(engine) as session:
        tx = session.get(Transaction, transaction_id)
        if not tx:
            return f"No se encontró una transacción con ID {transaction_id}."

        if amount is not None:
            tx.amount = amount
        if description is not None:
            tx.description = description
        if category is not None:
            tx.category = category
        if merchant is not None:
            tx.merchant = merchant
        if notes is not None:
            tx.notes = notes

        session.add(tx)
        session.commit()
        session.refresh(tx)

    return f"Transacción {transaction_id} actualizada ✓ — ${tx.amount:,.0f} en {tx.category}"
