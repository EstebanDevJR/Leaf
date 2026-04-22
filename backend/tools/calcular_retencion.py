from langchain_core.tools import tool

from backend.tools.get_uvt import get_uvt

# Tarifas de retención en la fuente (Art. 392 ET y decreto 1625/2016)
TARIFAS: dict[str, dict] = {
    "honorarios": {
        "label": "Honorarios",
        "tarifa_sin_empleados": 0.11,
        "tarifa_con_empleados": 0.10,
        "nota": "11% si no declara empleados, 10% si sí.",
    },
    "servicios": {
        "label": "Servicios generales",
        "tarifa": 0.04,
        "nota": "4% sobre valor bruto cuando supera 27 UVT.",
    },
    "consultoria": {
        "label": "Consultoría",
        "tarifa": 0.10,
        "nota": "10% sobre valor bruto.",
    },
    "arrendamiento": {
        "label": "Arrendamiento inmueble",
        "tarifa": 0.035,
        "nota": "3.5% cuando supera 27 UVT.",
    },
    "compras": {
        "label": "Compras",
        "tarifa": 0.025,
        "nota": "2.5% cuando supera 27 UVT.",
    },
    "transporte": {
        "label": "Transporte de carga",
        "tarifa": 0.01,
        "nota": "1% cuando supera 27 UVT.",
    },
}


@tool
def calcular_retencion(
    amount: float,
    concepto: str = "honorarios",
    tiene_empleados: bool = False,
) -> str:
    """Calcula la retención en la fuente para un pago a independiente en Colombia.

    Args:
        amount: Valor bruto del pago en COP.
        concepto: Tipo de ingreso. Opciones: honorarios, servicios, consultoria,
                  arrendamiento, compras, transporte.
        tiene_empleados: Para honorarios — True si el independiente tiene empleados
                         a cargo (aplica tarifa del 10% en lugar del 11%).
    """
    uvt = get_uvt()
    min_base = 27 * uvt  # Base mínima para la mayoría de conceptos

    info = TARIFAS.get(concepto.lower())
    if not info:
        opciones = ", ".join(TARIFAS.keys())
        return f"Concepto '{concepto}' no reconocido. Opciones: {opciones}"

    # Determinar tarifa
    if "tarifa_sin_empleados" in info:
        tarifa = info["tarifa_con_empleados" if tiene_empleados else "tarifa_sin_empleados"]
    else:
        tarifa = info["tarifa"]

    # Verificar base mínima (honorarios no tienen base mínima para personas naturales)
    if concepto != "honorarios" and amount < min_base:
        return (
            f"No aplica retención — el pago (${amount:,.0f}) es menor a "
            f"27 UVT (${min_base:,.0f}) para {info['label']}."
        )

    retencion = amount * tarifa
    neto = amount - retencion

    return (
        f"🧮 Retención en la fuente — {info['label']}:\n"
        f"  Valor bruto:   ${amount:,.0f}\n"
        f"  Tarifa:        {tarifa * 100:.1f}%\n"
        f"  Retención:     ${retencion:,.0f}\n"
        f"  Valor neto:    ${neto:,.0f}\n"
        f"\n📌 {info['nota']}\n"
        "⚠️ La retención la aplica quien paga, no quien recibe."
    )
