from langchain_core.tools import tool
from sqlmodel import Session

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def register_expense(
    amount: float,
    category: str,
    description: str,
    merchant: str = None,
    notes: str = None,
) -> str:
    """Registra un gasto en la base de datos.

    Args:
        amount: Monto del gasto en pesos colombianos (COP). Siempre positivo.
        category: Categoría del gasto. Opciones: comida, transporte, vivienda,
                  salud, entretenimiento, ropa, servicios, otro.
        description: Descripción breve del gasto.
        merchant: Nombre del comercio o establecimiento (opcional).
        notes: Notas adicionales (opcional).
    """
    tx = Transaction(
        amount=amount,
        description=description,
        category=category,
        type=TransactionType.expense,
        merchant=merchant,
        notes=notes,
    )
    with Session(engine) as session:
        session.add(tx)
        session.commit()
        session.refresh(tx)

    return f"Gasto registrado ✓ — ${amount:,.0f} en {category} (ID: {tx.id})"
