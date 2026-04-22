from langchain_core.tools import tool

from backend.tools.get_uvt import get_uvt


@tool
def calcular_deducciones(
    intereses_vivienda: float = 0,
    medicina_prepagada: float = 0,
    dependientes: int = 0,
    gmf_pagado: float = 0,
    aportes_voluntarios_pension: float = 0,
) -> str:
    """Calcula las deducciones y rentas exentas aplicables en la declaración de renta.

    Art. 119, 387, 126-1 ET — deducciones para personas naturales (asalariados e independientes).

    Args:
        intereses_vivienda: Intereses de crédito hipotecario pagados en el año (COP).
                            Deducción máx: 1.200 UVT.
        medicina_prepagada: Pagos de medicina prepagada y seguros de salud en el año (COP).
                            Deducción máx: 16 UVT/mes = 192 UVT/año.
        dependientes: Número de personas a cargo (hijos menores, padres, etc.).
                      Cada uno da derecho a descontar 10% del ingreso, máx 32 UVT/mes.
        gmf_pagado: GMF (4×1000) efectivamente pagado según extractos bancarios (COP).
                    Deducción: 50% del valor pagado.
        aportes_voluntarios_pension: Aportes voluntarios a fondos de pensión (COP).
                                     Deducción máx: 30% del ingreso bruto, máx 3.800 UVT.
    """
    uvt = get_uvt()

    deducciones = []
    total_deducciones = 0.0

    # 1. Intereses vivienda — Art. 119 ET
    if intereses_vivienda > 0:
        max_vivienda = 1_200 * uvt
        ded = min(intereses_vivienda, max_vivienda)
        total_deducciones += ded
        deducciones.append(
            f"  🏠 Intereses vivienda: ${ded:,.0f}"
            + (f" (limitado a ${max_vivienda:,.0f})" if intereses_vivienda > max_vivienda else "")
        )

    # 2. Medicina prepagada — Art. 387 ET
    if medicina_prepagada > 0:
        max_medicina = 192 * uvt  # 16 UVT/mes × 12
        ded = min(medicina_prepagada, max_medicina)
        total_deducciones += ded
        deducciones.append(
            f"  🏥 Medicina prepagada: ${ded:,.0f}"
            + (f" (limitado a ${max_medicina:,.0f})" if medicina_prepagada > max_medicina else "")
        )

    # 3. Dependientes — Art. 387 ET
    if dependientes > 0:
        # 10% del ingreso, máx 32 UVT/mes por dependiente → no podemos calcular sin ingreso
        # Calculamos el tope fijo: 32 UVT × 12 meses por dependiente
        max_por_dep = 32 * uvt * 12
        ded_dependientes = min(dependientes, 4) * max_por_dep  # máx 4 dependientes reconocidos
        total_deducciones += ded_dependientes
        deducciones.append(
            f"  👶 Dependientes ({dependientes}): hasta ${ded_dependientes:,.0f}/año "
            "(10% del ingreso, máx 32 UVT/mes c/u)"
        )

    # 4. GMF — Art. 115 ET
    if gmf_pagado > 0:
        ded = gmf_pagado * 0.50
        total_deducciones += ded
        deducciones.append(f"  4️⃣ GMF 50% deducible: ${ded:,.0f}")

    # 5. Aportes voluntarios pensión — Art. 126-1 ET
    if aportes_voluntarios_pension > 0:
        max_pension = 3_800 * uvt
        ded = min(aportes_voluntarios_pension, max_pension)
        total_deducciones += ded
        deducciones.append(
            f"  💰 Aportes vol. pensión: ${ded:,.0f}"
            + (f" (limitado a ${max_pension:,.0f})" if aportes_voluntarios_pension > max_pension else "")
        )

    if not deducciones:
        return (
            "No ingresaste valores para calcular deducciones. "
            "Proporciona intereses_vivienda, medicina_prepagada, dependientes, gmf_pagado "
            "o aportes_voluntarios_pension."
        )

    lines = [
        f"📋 Deducciones aplicables ({date_year()}):",
        "",
        *deducciones,
        "",
        f"  📊 Total deducciones estimadas: ${total_deducciones:,.0f}",
        "",
        "⚠️ Las deducciones reducen la renta líquida gravable. "
        "El beneficio real depende de tu tarifa marginal. Consulta a un contador.",
    ]
    return "\n".join(lines)


def date_year() -> int:
    from datetime import date
    return date.today().year
