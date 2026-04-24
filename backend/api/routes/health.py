"""Health report REST endpoint."""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/report")
def get_health_report() -> dict:
    """Genera el informe de salud financiera con score 0-100."""
    from backend.services.health_calculator import compute_health_score
    return compute_health_score()


@router.get("/take-home")
def get_take_home(sueldo_bruto: float) -> dict:
    """Calcula sueldo neto, descuentos y distribución recomendada."""
    from backend.services.tax_calculator import calcular_take_home
    return calcular_take_home(sueldo_bruto)


@router.get("/explain")
def explain_concept_endpoint(concept: str = Query(...)) -> dict:
    """Explica un concepto financiero colombiano en lenguaje simple."""
    from backend.tools.explain_concept import CONCEPTS
    key = concept.lower().strip()
    if key in CONCEPTS:
        explanation = CONCEPTS[key]
    else:
        match = next(
            (v for k, v in CONCEPTS.items() if key in k or k in key or any(w in k for w in key.split())),
            None,
        )
        if not match:
            available = list(CONCEPTS.keys())
            return {"found": False, "concept": concept, "available": available, "explanation": ""}
        explanation = match
    return {
        "found": True,
        "concept": concept,
        "explanation": f"📚 {concept.upper()}\n\n{explanation}\n\n⚠️ Información educativa general.",
    }


@router.get("/cdt-comparison")
def get_cdt_comparison(monto: float = 0, plazo: int = 12) -> dict:
    """Compara tasas CDT con cálculo de retención y rentabilidad neta."""
    from backend.tools.cdt_live_rates import _get_rates
    RETENCION = 0.07  # 7% retención en la fuente sobre rendimientos CDT
    INFLACION = 0.055  # 5.5% proyectado 2026

    rates, is_live, source_date = _get_rates()
    valid_terms = [3, 6, 12, 24]
    term = min(valid_terms, key=lambda t: abs(t - plazo))

    banks = []
    for bank, terms in rates.items():
        rate_ea = terms.get(term, 0)
        if not rate_ea:
            continue
        rendimiento_bruto = monto * (rate_ea / 100) * (term / 12) if monto else 0
        retencion_pesos = round(rendimiento_bruto * RETENCION)
        rendimiento_neto = round(rendimiento_bruto - retencion_pesos)
        monto_final = round(monto + rendimiento_neto) if monto else 0
        tasa_neta = rate_ea * (1 - RETENCION)
        tasa_real = tasa_neta - INFLACION

        banks.append({
            "bank": bank,
            "rate_ea": rate_ea,
            "tasa_neta_ea": round(tasa_neta, 2),
            "tasa_real_ea": round(tasa_real, 2),
            "beats_inflation": tasa_real > 0,
            "rendimiento_bruto": round(rendimiento_bruto),
            "retencion": retencion_pesos,
            "rendimiento_neto": rendimiento_neto,
            "monto_final": monto_final,
        })

    banks.sort(key=lambda b: -b["tasa_neta_ea"])

    return {
        "is_live": is_live,
        "source_date": source_date,
        "plazo_meses": term,
        "monto": monto,
        "retencion_pct": RETENCION * 100,
        "inflacion_pct": INFLACION * 100,
        "banks": banks,
        "best": banks[0] if banks else None,
    }
