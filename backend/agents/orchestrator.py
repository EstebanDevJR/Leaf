"""Orquestador Leaf — routing por dominio con agentes especializados."""

from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from backend.agents.dian import DIAN_TOOLS
from backend.agents.insights import INSIGHTS_TOOLS
from backend.agents.investigador import _get_investigador_tools
from backend.agents.ocr import OCR_TOOLS
from backend.agents.router import classify_intent
from backend.agents.transactions import TRANSACTION_TOOLS
from backend.config import settings
from backend.tools.cdt_live_rates import get_live_cdt_rates
from backend.tools.check_budget import check_budget
from backend.tools.dian_factura import import_dian_factura
from backend.tools.explain_concept import explain_concept
from backend.tools.formulario_210 import formulario_210
from backend.tools.health_tools import generate_financial_health_report
from backend.tools.savings_goal_tools import SAVINGS_GOAL_TOOLS
from backend.tools.take_home_tools import calculate_take_home_pay
from backend.tools.whatif_simulator import whatif_simulator

_BASE = """Eres Leaf 🌿, asistente financiero personal para Colombia. Responde siempre en español colombiano, conciso y amigable.

Montos COP: "mil"/"luca" = 1.000 | "palo"/"millón" = 1.000.000. Sin unidad = pesos.
Categorías gastos: comida, transporte, vivienda, salud, entretenimiento, ropa, servicios, otro.
Categorías ingresos: salario, freelance, ventas, inversiones, otro."""

_PROMPTS = {
    "transacciones": _BASE + """

Confirma cada transacción con monto, categoría e ID. Tras registrar un gasto llama check_budget si hay presupuesto configurado y avisa si supera el 80%.""",

    "dian": _BASE + """

Usa los tools DIAN según la consulta. Siempre aclara que los cálculos son estimaciones y recomienda un contador.""",

    "insights": _BASE + """

Usa check_budget, set_budget, predict_expenses y summarize_month según la consulta. Da contexto financiero claro.""",

    "investigador": _BASE + """

Analiza patrones, anomalías, suscripciones, metas y CDT. Genera insights accionables con disclaimer en tasas CDT.""",

    "ocr": _BASE + """

Extrae los datos del recibo y confirma los valores antes de registrar la transacción.""",

    "general": _BASE + """

Transacciones: confirma con monto, categoría e ID. Tras registrar gasto verifica presupuesto si está configurado.
DIAN: estimaciones — recomienda contador. CDT/tasas: siempre con disclaimer legal.
Metas: usa create/list/update_savings_goal. Simulador: escenarios ahorro_mas, gasto_menos, ingreso_mas, categoria_cero.""",
}

_memory = MemorySaver()
_agents: dict[str, object] = {}
_session_domains: dict[str, str] = {}
_llm = None


def _get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            num_ctx=settings.ollama_num_ctx,
        )
    return _llm


def _tool_map() -> dict[str, list]:
    inv_tools = _get_investigador_tools()
    all_tools = (
        TRANSACTION_TOOLS + OCR_TOOLS + INSIGHTS_TOOLS + DIAN_TOOLS
        + inv_tools + SAVINGS_GOAL_TOOLS
        + [whatif_simulator, formulario_210, get_live_cdt_rates, import_dian_factura,
           calculate_take_home_pay, generate_financial_health_report, explain_concept]
    )
    return {
        "transacciones": TRANSACTION_TOOLS + [check_budget],
        "dian":          DIAN_TOOLS + [formulario_210, import_dian_factura],
        "insights":      INSIGHTS_TOOLS + SAVINGS_GOAL_TOOLS + [whatif_simulator, generate_financial_health_report, calculate_take_home_pay],
        "investigador":  inv_tools + [get_live_cdt_rates, explain_concept],
        "ocr":           OCR_TOOLS + TRANSACTION_TOOLS,
        "general":       all_tools,
    }


def get_agent(message: str = "", session_id: str | None = None):
    if session_id and session_id in _session_domains:
        intent = _session_domains[session_id]
    else:
        intent = classify_intent(message) if message else "general"
        if session_id:
            _session_domains[session_id] = intent
    if intent not in _agents:
        tools = _tool_map()[intent]
        _agents[intent] = create_react_agent(
            _get_llm(), tools, prompt=_PROMPTS[intent], checkpointer=_memory
        )
    return _agents[intent]
