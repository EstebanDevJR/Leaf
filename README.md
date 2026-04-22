# Leaf 🌿

**Agente financiero personal colombiano — local-first, multi-agente, open source.**

Sin nube. Sin suscripciones. Tus datos en tu máquina.

## Inicio rápido

```bash
# 1. Clonar
git clone https://github.com/tu-usuario/leaf.git
cd leaf

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Levantar todo con Docker Compose
docker compose up

# 4. Descargar el modelo LLM (primera vez)
docker compose exec ollama ollama pull gemma4:e4b
```

La app estará en http://localhost:5173 y la API en http://localhost:8000.

## Desarrollo local

### Backend

```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalar dependencias
uv sync

# Correr backend
uv run uvicorn backend.main:app --reload
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

## Arquitectura

```
leaf/
├── backend/
│   ├── agents/       # Orquestador LangGraph + agentes especializados
│   ├── tools/        # Herramientas tipadas por agente
│   ├── api/          # FastAPI routes
│   ├── db/           # SQLite engine + session
│   └── models/       # SQLModel (Pydantic + SQLAlchemy)
├── frontend/         # SvelteKit
├── openclaw-skill/   # Skill para OpenClaw
└── docker-compose.yml
```

## Stack

| Capa     | Tecnología         |
|----------|--------------------|
| Agentes  | LangGraph          |
| LLM      | Ollama + gemma3    |
| API      | FastAPI + Python   |
| ORM      | SQLModel           |
| DB       | SQLite → Turso     |
| Frontend | SvelteKit          |
| Paquetes | uv                 |
| Infra    | Docker Compose     |

## Roadmap

- [x] **Fase 1** — Core: orquestador + transacciones + SQLite + FastAPI + SvelteKit
- [ ] **Fase 2** — OCR de recibos (Moondream2)
- [ ] **Fase 3** — Insights + presupuestos
- [ ] **Fase 4** — Skill de OpenClaw (WhatsApp/Telegram/Discord)
- [ ] **Fase 5** — Reportes DIAN

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md).

---

*Leaf 🌿 — hecho en Colombia, para el mundo.*
