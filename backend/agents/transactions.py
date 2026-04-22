"""Agente de transacciones — expone las tools tipadas del dominio financiero."""

from backend.tools.delete_transaction import delete_transaction
from backend.tools.edit_transaction import edit_transaction
from backend.tools.query_history import query_history
from backend.tools.register_expense import register_expense
from backend.tools.register_income import register_income

TRANSACTION_TOOLS = [
    register_expense,
    register_income,
    edit_transaction,
    query_history,
    delete_transaction,
]
