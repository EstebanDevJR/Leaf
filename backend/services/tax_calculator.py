"""Calculadora de retención en la fuente y nómina — tabla DIAN 2026."""

# Valores vigentes 2026
UVT_2026 = 47_065.0          # COP por UVT
SMMLV_2026 = 1_423_500.0     # Salario mínimo mensual legal vigente 2026

# Porcentajes seguridad social (cargo empleado)
SALUD_PCT = 0.04
PENSION_PCT = 0.04
# Fondo de solidaridad pensional: aplica a partir de 4 SMMLV
SOLIDARIDAD_UMBRAL = 4 * SMMLV_2026
SOLIDARIDAD_PCT_BASE = 0.01   # 1% entre 4-16 SMMLV
SOLIDARIDAD_PCT_ALTO = 0.012  # 1.2% entre 16-17 SMMLV (y escala hasta 2%)

# Exención laboral: 25% del ingreso laboral (art. 206 ET), límite 240 UVT/año → 20 UVT/mes
EXENCION_PCT = 0.25
EXENCION_LIMITE_MENSUAL = 20 * UVT_2026  # ~$941.300

# Tabla marginal retención en la fuente (rangos en UVT/mes, tasa marginal)
# Fuente: tabla del art. 383 ET actualizada con UVT 2026
_TABLA_RETENCION = [
    (0,   95,   0.0,    0.0),       # 0 a 95 UVT: 0%
    (95,  150,  0.19,   0.0),       # 95 a 150 UVT: 19%
    (150, 360,  0.28,   10.44),     # 150 a 360 UVT: 28%
    (360, 640,  0.33,   69.24),     # 360 a 640 UVT: 33%
    (640, 9999, 0.35,   162.24),    # > 640 UVT: 35%
]
# Fórmula: retencion_uvt = (base_gravable_uvt - lim_inf_uvt) * tasa + suma_tecnica


def calcular_seguridad_social(sueldo_bruto: float) -> dict[str, float]:
    salud = sueldo_bruto * SALUD_PCT
    pension = sueldo_bruto * PENSION_PCT

    solidaridad = 0.0
    if sueldo_bruto >= SOLIDARIDAD_UMBRAL:
        solidaridad = sueldo_bruto * SOLIDARIDAD_PCT_BASE
    if sueldo_bruto >= 16 * SMMLV_2026:
        solidaridad = sueldo_bruto * SOLIDARIDAD_PCT_ALTO

    return {
        "salud": round(salud),
        "pension": round(pension),
        "solidaridad": round(solidaridad),
        "total": round(salud + pension + solidaridad),
    }


def calcular_retencion_fuente(sueldo_bruto: float, ss: dict[str, float]) -> float:
    """Retención en la fuente para asalariados (método simplificado DIAN 2026)."""
    # Base gravable = bruto - SS - exención 25% (limitada a 20 UVT/mes)
    descuentos_ss = ss["salud"] + ss["pension"] + ss["solidaridad"]
    ingreso_neto = sueldo_bruto - descuentos_ss
    exencion = min(ingreso_neto * EXENCION_PCT, EXENCION_LIMITE_MENSUAL)
    base_gravable = max(0.0, ingreso_neto - exencion)

    base_uvt = base_gravable / UVT_2026

    retencion_uvt = 0.0
    for lim_inf, lim_sup, tasa, suma_tec in _TABLA_RETENCION:
        if base_uvt > lim_inf:
            exceso = min(base_uvt, lim_sup) - lim_inf
            retencion_uvt = exceso * tasa + suma_tec
        if base_uvt <= lim_sup:
            break

    return round(retencion_uvt * UVT_2026)


def calcular_take_home(sueldo_bruto: float) -> dict:
    ss = calcular_seguridad_social(sueldo_bruto)
    retencion = calcular_retencion_fuente(sueldo_bruto, ss)

    total_descuentos = ss["total"] + retencion
    sueldo_neto = sueldo_bruto - total_descuentos

    # Distribución 50/30/20
    ahorro_20 = round(sueldo_neto * 0.20)
    gustos_30 = round(sueldo_neto * 0.30)
    necesidades_50 = round(sueldo_neto * 0.50)

    # Proyecciones ahorro
    ahorro_anual = ahorro_20 * 12
    cdt_12m_rate = 0.115  # tasa CDT referencia 12 meses
    cdt_rendimiento = round(ahorro_anual * cdt_12m_rate)

    return {
        "sueldo_bruto": round(sueldo_bruto),
        "descuentos": {
            "salud": ss["salud"],
            "pension": ss["pension"],
            "solidaridad": ss["solidaridad"],
            "retencion_fuente": retencion,
            "total": total_descuentos,
        },
        "sueldo_neto": round(sueldo_neto),
        "pct_descuento": round(total_descuentos / sueldo_bruto * 100, 1) if sueldo_bruto else 0,
        "distribucion": {
            "necesidades_50pct": necesidades_50,
            "gustos_30pct": gustos_30,
            "ahorro_20pct": ahorro_20,
        },
        "proyecciones": {
            "ahorro_mensual": ahorro_20,
            "ahorro_anual": ahorro_anual,
            "cdt_rendimiento_1a": cdt_rendimiento,
            "total_con_cdt": ahorro_anual + cdt_rendimiento,
        },
    }
