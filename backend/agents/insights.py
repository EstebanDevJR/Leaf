"""Agente de insights — presupuestos, predicciones y resumen mensual."""

from backend.tools.check_budget import check_budget
from backend.tools.predict_expenses import predict_expenses
from backend.tools.set_budget import set_budget
from backend.tools.summarize_month import summarize_month

INSIGHTS_TOOLS = [check_budget, set_budget, predict_expenses, summarize_month]
