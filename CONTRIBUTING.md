# Contribuir a Leaf 🌿

Gracias por tu interés en Leaf. Este documento explica cómo contribuir.

## Setup de desarrollo

```bash
# Fork + clone
git clone https://github.com/tu-usuario/leaf.git
cd leaf

# Backend
cp .env.example .env
uv sync

# Frontend
cd frontend && npm install && cd ..

# Ollama
ollama pull gemma3
```

## Estructura de branches

- `main` — estable, siempre deployable
- `feat/nombre` — nuevas funcionalidades
- `fix/nombre` — bugfixes
- `chore/nombre` — mantenimiento

## Cómo agregar un nuevo agente

1. Crea `backend/agents/tu_agente.py`
2. Define las tools en `backend/tools/`
3. Registra las tools en `backend/agents/orchestrator.py`
4. Agrega rutas en `backend/api/routes/` si es necesario

## Tests

```bash
uv run pytest
```

## PR checklist

- [ ] Tests pasan
- [ ] No se rompen endpoints existentes
- [ ] El código corre con `ollama pull gemma3`
- [ ] Sin API keys hardcodeadas

## Filosofía

- **Local-first**: todo debe funcionar sin internet (excepto la descarga inicial de Ollama)
- **Sin magia**: LangGraph sobre abstracciones opacas
- **Colombiano por diseño**: COP, DIAN, contexto local

---

¿Dudas? Abre un issue.
