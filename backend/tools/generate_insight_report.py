from langchain_core.tools import tool

from backend.tools.analyze_patterns import analyze_patterns
from backend.tools.detect_anomaly import detect_anomaly
from backend.tools.emergency_fund_status import emergency_fund_status
from backend.tools.find_idle_money import find_idle_money
from backend.tools.find_subscriptions import find_subscriptions


@tool
def generate_insight_report(period_days: int = 30) -> str:
    """Genera un informe completo de hallazgos financieros consolidando todos los análisis.

    Args:
        period_days: Período base del análisis en días (default 30).
    """
    separator = "\n" + "─" * 50 + "\n"
    sections = [f"📋 INFORME FINANCIERO — últimos {period_days} días\n{'═'*50}\n"]

    def _run(label: str, fn, **kwargs) -> str:
        try:
            result = fn.invoke(kwargs)
            return f"{label}\n{result}"
        except Exception as e:
            return f"{label}\nNo disponible: {e}"

    sections.append(_run("1. PATRONES DE GASTO", analyze_patterns, category="all", period_days=period_days))
    sections.append(_run("2. ANOMALÍAS DETECTADAS", detect_anomaly, category="all"))
    sections.append(_run("3. SUSCRIPCIONES Y PAGOS RECURRENTES", find_subscriptions, period_days=max(period_days, 90)))
    sections.append(_run("4. DINERO INACTIVO", find_idle_money))
    sections.append(_run("5. FONDO DE EMERGENCIA", emergency_fund_status))

    return separator.join(sections)
