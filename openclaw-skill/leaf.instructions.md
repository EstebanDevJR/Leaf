# Leaf — Instrucciones para OpenClaw

## Qué hace Leaf

Leaf es un agente financiero personal para Colombia. Vive en la máquina del usuario (100% local, sin nube).
Desde OpenClaw puedes hablarle en español natural y él decide qué herramienta usar.

## Cuándo invocar Leaf

Invoca Leaf cuando el usuario mencione:
- Gastos o compras: "gasté", "pagué", "compré", "me cobró"
- Ingresos: "me pagaron", "recibí", "ingresó"
- Presupuesto: "¿cómo voy?", "presupuesto", "límite"
- Resumen financiero: "¿cómo estoy?", "resumen del mes", "¿qué gasté?"
- Impuestos: "renta", "DIAN", "declarar"
- Fechas DIAN: "fecha límite", "plazo declaración"

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

## Formato de respuesta esperado

Leaf responde en texto plano, en español colombiano, conciso. No uses markdown complejo en mensajes de chat.
El resultado del tool ya viene formateado — repítelo directamente al usuario sin reformatear.

## Privacidad

Leaf corre 100% local. Ningún dato financiero sale de la máquina del usuario.
OpenClaw solo transmite el mensaje de texto (y opcionalmente imágenes de recibos) al servidor local de Leaf.

## Notas de integración

- `base_url` es `http://localhost:8000` por defecto. El usuario puede cambiarlo en su config de OpenClaw si usa un puerto diferente.
- El endpoint `/chat/stream` responde con Server-Sent Events (SSE). OpenClaw debe consumir el stream hasta el evento `{"type":"done"}`.
- Si el usuario sube una foto, envíala como mensaje normal — Leaf tiene OCR vía Ollama vision.
