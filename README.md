# Leaf 🌿

**Agente financiero personal colombiano — local-first, multi-agente, open source.**

Sin nube. Sin suscripciones. Tus datos en tu máquina.

## Inicio rápido

```bash
# 1. Clonar
git clone https://github.com/EstebanDevJR/Leaf.git
cd leaf

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Levantar todo con Docker Compose
docker compose up

# 4. Descargar el modelo LLM (primera vez)
docker compose exec ollama ollama pull gemma4:e4b
```

La app estará en http://localhost:5173 y la API en http://localhost:8000.

> Los modelos de voz (Whisper STT y Piper TTS) se descargan automáticamente al iniciar el servidor.

## Desarrollo local

### Backend

```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalar dependencias
uv sync

# Correr backend (solo observa backend/; evita recargas por cambios en .venv)
uv run uvicorn backend.main:app --reload --reload-dir backend
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Ollama (LLM local)

```bash
# Instalar Ollama: https://ollama.com
ollama pull gemma4:e4b
```

## Agentes

Leaf tiene seis agentes especializados orquestados por un ReAct central:

| Agente | Rol |
|--------|-----|
| **Orquestador** | Coordina todos los agentes y responde en chat |
| **Transacciones** | Registra, edita y consulta gastos e ingresos |
| **Insights** | Presupuestos, predicciones y resumen mensual |
| **DIAN** | Impuesto de renta, retención, GMF y fechas límite |
| **OCR** | Extrae datos de recibos con Moondream2 |
| **Investigador** | Monitoreo autónomo en background con toggle ON/OFF |

### Agente Investigador

Corre en segundo plano y actúa sin que el usuario lo pida:

- **08:00 diario** — detecta dinero inactivo y anomalías de gasto.
- **Por cada transacción** — evalúa si el gasto de la categoría es anómalo vs. el historial.
- **Manual** — `POST /investigador/run` para dispararlo en cualquier momento.

Herramientas disponibles también desde el chat:

```
analyze_patterns       tendencias de gasto vs. período anterior
detect_anomaly         alerta si el gasto supera 50% del promedio histórico
find_subscriptions     pagos recurrentes y suscripciones activas
calculate_savings_goal proyección de meta de ahorro con escenarios
get_cdt_rates          tasas CDT de referencia en bancos colombianos
analyze_weekday        distribución de gastos por día de semana
find_idle_money        balance acumulado sin movimiento reciente
emergency_fund_status  cobertura del fondo de emergencia en meses
generate_insight_report informe completo de todos los hallazgos
explain_concept        educación financiera (CDT, UVT, GMF, renta…)
```

Toggle ON/OFF:

```bash
curl -X POST http://localhost:8000/investigador/toggle \
  -H "Content-Type: application/json" -d '{"enabled": false}'

curl http://localhost:8000/investigador/status
```

## Voz

Leaf incluye procesamiento de voz completamente local — sin APIs externas, sin costo.

### Telegram Voice Bot

Envía un mensaje de voz al bot y responde hablando.

```
Usuario → audio OGG  →  Whisper STT  →  Orquestador  →  Piper TTS  →  audio OGG
```

Configura el bot en `.env` y el resto es automático.

### Llamada de voz desde la Web

Haz clic en **🎙️ Hablar con Leaf** en la barra superior para abrir una sesión de voz en tiempo real directamente desde el navegador. El agente transcribe tu audio, razona y responde en voz.

```
Browser (MediaRecorder) → WebSocket /voice/ws → Whisper → Orquestador → Piper → audio
```

### Modelos de voz

Los modelos se descargan automáticamente al primer uso:

| Modelo | Tamaño | Destino | Rol |
|--------|--------|---------|-----|
| Phi-4-multimodal-instruct | ~8 GB | `~/.cache/huggingface/` | STT principal (audio nativo) |
| Whisper `small` | ~244 MB | `~/.cache/huggingface/` | STT fallback |
| Piper TTS español | ~65 MB | `./models/` | Síntesis de voz |

Phi-4-multimodal recibe el audio directamente — sin conversión a texto previa — lo que mejora la comprensión de frases financieras en español colombiano. Si no carga (VRAM insuficiente), el sistema cae automáticamente a faster-whisper.

## Telegram Bot (texto)

```env
TELEGRAM_BOT_TOKEN=123456:ABCdef...   # obtenlo con @BotFather
TELEGRAM_CHAT_ID=987654321            # tu chat ID personal
```

Comandos: `/start`, `/gastos`, `/resumen`, `/metas`, `/alertas`  
Texto libre y mensajes de voz son procesados directamente por el agente.

## Variables de entorno

```env
DATABASE_URL=sqlite:///./leaf.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e4b
OLLAMA_VISION_MODEL=gemma4:e4b
DEBUG=false

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Voz (opcional — modelos se auto-descargan)
WHISPER_MODEL_SIZE=small                              # fallback STT
PIPER_VOICE_PATH=models/es_ES-davefx-medium.onnx
OLLAMA_VOICE_MODEL=phi4                               # LLM con herramientas financieras
PHI4_VOICE_MODEL=microsoft/Phi-4-multimodal-instruct  # STT multimodal principal
```

## Arquitectura

```
leaf/
├── backend/
│   ├── agents/           # Orquestador LangGraph + agentes especializados
│   ├── tools/            # 40+ herramientas tipadas
│   ├── api/routes/       # chat, transactions, budgets, alerts, investigador,
│   │                     # ocr, savings_goals, import_export, profiles, voice
│   ├── voice/            # VoicePipeline (STT → LLM → TTS)
│   ├── services/         # alert_checker, telegram_bot, voice_stt,
│   │                     # voice_tts, model_downloader
│   ├── scheduler.py      # Job diario 08:00 + hook on_new_transaction
│   ├── db/               # SQLite engine + session
│   └── models/           # Transaction, Budget, Alert, InvestigadorConfig,
│                         # SavingsGoal, UserProfile
├── frontend/
│   └── src/lib/
│       ├── components/   # Chat, TransactionDrawer, SavingsGoals, etc.
│       └── voice/        # CallButton.svelte + WebRTCHandler.ts
├── models/               # Piper TTS (auto-descargado)
└── docker-compose.yml
```

## Stack

| Capa | Tecnología |
|------|------------|
| Agentes | LangGraph |
| LLM | Ollama + gemma4 |
| LLM voz | Ollama + phi-4 |
| STT | Phi-4-multimodal (HuggingFace) + faster-whisper (fallback) |
| TTS | Piper TTS |
| API | FastAPI + Python 3.11 |
| ORM | SQLModel |
| DB | SQLite |
| Frontend | SvelteKit + Svelte 5 |
| Exportación | fpdf2 + openpyxl |
| Mensajería | python-telegram-bot |
| HTTP client | httpx |
| Paquetes | uv |
| Infra | Docker Compose |

## API

```
POST   /chat/stream              chat con streaming SSE (token a token)
GET    /transactions/            historial de transacciones
GET    /transactions/stats       resumen mensual (ingresos, gastos, balance)
POST   /transactions/            crear transacción
PATCH  /transactions/{id}        editar transacción
DELETE /transactions/{id}        eliminar transacción
GET    /budgets/                 listar presupuestos
PUT    /budgets/{category}       crear/actualizar presupuesto
GET    /alerts/                  alertas activas
POST   /alerts/{id}/dismiss      descartar alerta
POST   /ocr/extract              extraer datos de recibo (imagen)
GET    /investigador/status      estado del toggle del Investigador
POST   /investigador/toggle      activar / desactivar Investigador
POST   /investigador/run         disparar análisis manual
GET    /savings-goals/           listar metas de ahorro
POST   /savings-goals/           crear meta de ahorro
PATCH  /savings-goals/{id}       actualizar meta (aportes, monto, etc.)
DELETE /savings-goals/{id}       eliminar meta
POST   /io/csv?bank=X            importar CSV bancario
POST   /io/dian-factura          importar factura electrónica XML
GET    /io/excel                 exportar mes a Excel
GET    /io/pdf?mode=standard     exportar mes a PDF
GET    /io/pdf?mode=contador     exportar en modo contador
GET    /profiles/                listar perfiles familiares
POST   /profiles/                crear perfil
DELETE /profiles/{id}            eliminar perfil
WS     /voice/ws                 sesión de voz en tiempo real
POST   /voice/chat               transcripción + respuesta en audio (REST)
GET    /health                   estado del servicio
```

## Roadmap

- [x] Core: orquestador + transacciones + SQLite + FastAPI + SvelteKit
- [x] OCR de recibos (Moondream2)
- [x] Insights + presupuestos
- [x] Reportes DIAN
- [x] Agente Investigador autónomo (10 herramientas, monitoreo en background)
- [x] Metas de ahorro inteligentes con proyecciones ajustadas por inflación
- [x] Dashboard visual completo — cashflow, categorías, patrimonio neto
- [x] Importación masiva CSV (Bancolombia, Davivienda, Nequi, Nubank, Daviplata)
- [x] Exportación profesional PDF + Excel + Modo Contador
- [x] Formulario 210 — declaración de renta preliminar
- [x] Simulador de escenarios What-If
- [x] Telegram bot — texto + voz + notificaciones push del Investigador
- [x] Multi-perfil familiar
- [x] Importación de facturas electrónicas DIAN (UBL XML)
- [x] CDT con tasas en vivo
- [x] Streaming token a token en el chat
- [x] Voz local (Whisper STT + Piper TTS) — Telegram y Web

---

*Leaf 🌿 — hecho en Colombia, para el mundo.*
