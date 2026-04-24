# Leaf — Instrucciones para OpenClaw

## Qué hace Leaf

Leaf es un agente financiero personal para Colombia. Vive en la máquina del usuario (100% local, sin nube).
Desde OpenClaw puedes hablarle en español natural y él decide qué herramienta usar.

## Cuándo invocar Leaf

Invoca Leaf cuando el usuario mencione cualquiera de estas áreas:

**Transacciones**
- Gastos o compras: "gasté", "pagué", "compré", "me cobró"
- Ingresos: "me pagaron", "recibí", "ingresó"
- Editar/borrar: "corrige ese gasto", "elimina esa transacción"

**Presupuesto y análisis**
- "¿cómo voy?", "presupuesto", "límite", "categoría"
- "¿qué gasté esta semana?", "resumen del mes"
- "mis patrones de gasto", "¿en qué día gasto más?"
- "transacciones raras", "gasto anormal", "anomalía"
- "¿cuánto gastaré este mes?", "predice mis gastos"

**Metas de ahorro**
- "quiero ahorrar para", "meta de ahorro", "cuánto me falta para"
- "¿cómo voy con mis metas?", "nueva meta"

**Fondo de emergencia**
- "fondo de emergencia", "¿cuántos meses de gastos tengo?", "colchón"

**Simulador what-if**
- "¿qué pasa si ahorro X%?", "si reduzco mis gastos en...", "simula"
- "proyección", "¿cuánto tendría en un año si?"

**CDT e inversiones**
- "tasas CDT", "¿dónde invierto?", "mejor CDT"
- "¿cuánto gano si pongo X en un CDT?", "comparar CDT"
- "CDT a 12 meses", "Bancolombia vs Davivienda CDT"

**Sueldo neto / take-home**
- "¿cuánto me queda de mi sueldo?", "descuentos de nómina"
- "salario neto", "retención en la fuente de mi salario", "cuánto me llega"

**Salud financiera**
- "¿cómo está mi salud financiera?", "mi score financiero"
- "informe de salud", "¿qué tan bien manejo mi plata?"

**Suscripciones**
- "¿qué suscripciones tengo?", "pagos recurrentes"
- "suscripciones sin usar", "¿cuánto pago en suscripciones?"

**Conceptos financieros**
- "¿qué es un CDT?", "explícame el GMF", "¿qué es UVT?"
- "cómo funciona el interés compuesto", "qué es un ETF"
- Conceptos: CDT, UVT, GMF, retención, inflación, interés compuesto,
  fondo de emergencia, TES, ETF, FOGAFÍN, pensión, patrimonio neto,
  diversificación, presupuesto 50/30/20, tasa EA, SMMLV

**Impuestos DIAN**
- "renta", "DIAN", "declarar", "formulario 210"
- "retención en la fuente", "¿debo declarar?"
- Fechas límite: "¿cuándo debo declarar?"

**GMF y deducciones**
- "¿cuánto me cobran de 4x1000?", "GMF de esta transferencia"
- "deducciones de nómina"

**Recibos y facturas**
- Imagen de recibo adjunta → OCR automático + registro de gasto

## Cómo habla el usuario colombiano

Leaf entiende colombianismos monetarios:
- `luca` = $1.000 COP
- `palo` = $1.000.000 COP
- `mil` = $1.000 COP
- Cantidades sin unidad → se asume COP

Ejemplos reales:
- "gasté 80 lucas en el Éxito" → `register_expense(80000, "comida", "compras Éxito", "Éxito")`
- "me llegaron 3 palos de salario" → `register_income(3000000, "salario", "salario mensual")`
- "¿cómo voy en comida?" → `check_budget("comida")`
- "¿cuánto me queda de 4 palos?" → `calculate_take_home(4000000)`
- "compara CDT a 12 meses" → `get_live_cdt_rates(12)`
- "¿cómo está mi salud financiera?" → `generate_financial_health_report()`
- "quiero ahorrar 10 palos para un viaje en 8 meses" → `calculate_savings_goal(...)`
- "¿qué es el GMF?" → `explain_concept("GMF")`

## Formato de respuesta esperado

Leaf responde en texto plano, en español colombiano, conciso. No uses markdown complejo en mensajes de chat.
El resultado del tool ya viene formateado — repítelo directamente al usuario sin reformatear.

## Privacidad

Leaf corre 100% local. Ningún dato financiero sale de la máquina del usuario.
OpenClaw solo transmite el mensaje de texto (y opcionalmente imágenes de recibos) al servidor local de Leaf.

## Notas de integración

- `base_url` es `http://localhost:8000` por defecto. El usuario puede cambiarlo en su config de OpenClaw si usa un puerto diferente.
- El endpoint `/chat/stream` responde con Server-Sent Events (SSE). OpenClaw debe consumir el stream hasta el evento `{"type":"done"}`.
- Si el usuario sube una foto de recibo, envíala como mensaje normal — Leaf tiene OCR vía Ollama vision.
- Las tasas CDT provienen de la Superfinanciera (SFC) vía datos.gov.co, actualizadas diariamente.
