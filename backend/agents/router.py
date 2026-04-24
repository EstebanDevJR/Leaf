"""Clasificador de intento por dominio — sin llamada al LLM."""

import re

_PATTERNS: dict[str, list[str]] = {
    "transacciones": [
        r"\bregistra\b", r"\bgastos?\b", r"\bingresos?\b",
        r"\bgast[eé]\b", r"\bpagu[eé]\b", r"\bcompr[eé]\b", r"\bcobr[eé]\b",
        r"\bedita?\b", r"\bborra\b", r"\belimina\b", r"\bhistorial\b",
        r"\bmovimientos?\b", r"\btransacci[oó]n(es)?\b",
        r"\b\d+\s*(mil|luca|palo|mill[oó]n|millones|k)\b",
        r"\$\s*\d+",
    ],
    "dian": [
        r"\bimpuestos?\b", r"\brenta\b", r"\bdian\b", r"\bdeclar(ar|aci[oó]n)\b",
        r"\bretenci[oó]n\b", r"\bgmf\b", r"\b4\s*x?\s*1000\b", r"\bdeducci[oó]n(es)?\b",
        r"\buvt\b", r"\btribut\w+\b", r"\bborrador\b", r"\bformulario\b",
        r"\bfactura\s+electr[oó]nica\b", r"\bnit\b", r"\bpatrimonio\b",
        r"\bobligad[oa]\b", r"\bplazo[s]?\s+(dian|tributari)\b",
    ],
    "insights": [
        r"\bpresupuesto\b", r"\bl[ií]mites?\b", r"\bpredicci[oó]n\b",
        r"\bproyecci[oó]n\b", r"\bresumen\s+de[l]?\s+mes\b", r"\bmensual\b",
        r"\bcu[aá]nto\s+(gast[eé]|tengo|llevo)\b",
        r"\bsalud\s+financiera\b", r"\bscore\s+financiero\b",
    ],
    "investigador": [
        r"\banaliza\b", r"\bpatr[oó]n(es)?\b", r"\banomal[ií]as?\b",
        r"\bsuscripci[oó]n(es)?\b", r"\bmeta[s]?\s+de\s+ahorro\b",
        r"\bcdt\b", r"\bfondo\s+de\s+emergencia\b",
        r"\btendencias?\b", r"\binsights?\b", r"\binforme\s+financiero\b",
        r"\bqu[eé]\s+d[ií]as?\b", r"\bgastos?\s+por\s+semana\b",
    ],
    "ocr": [
        r"\bfoto\b", r"\bimagen\b", r"\brecibo\b", r"\bescanea\b", r"\bticket\b",
        r"\bfactura\b",
    ],
}

_compiled: dict[str, list[re.Pattern]] = {
    domain: [re.compile(p, re.IGNORECASE) for p in pats]
    for domain, pats in _PATTERNS.items()
}


def classify_intent(message: str) -> str:
    """Retorna el dominio con más coincidencias, o 'general' si hay empate o ninguna."""
    scores = {
        domain: sum(1 for p in pats if p.search(message))
        for domain, pats in _compiled.items()
    }
    best_score = max(scores.values())
    if best_score == 0:
        return "general"
    winners = [d for d, s in scores.items() if s == best_score]
    return winners[0] if len(winners) == 1 else "general"
