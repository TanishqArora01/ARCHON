# Archon

Archon is a repository intelligence platform for AI Staff Engineer workflows.
It builds deterministic repository context before invoking any model:

Repository -> Snapshot -> Parsing -> Symbol Resolution -> Graph -> Impact -> Retrieval -> Agents -> Evidence-backed recommendations

## Current Application Surface

- FastAPI application: `src.api.app:app`
- Webhook endpoint: `POST /api/v1/webhooks/vcs`
- Health endpoint: `GET /healthz`
- Version endpoint: `GET /api/v1/version`
- CLI/server entrypoint: `python main.py` or `archon-api`

## Local Services

Archon is designed for self-hosted local infrastructure:

- PostgreSQL for repository metadata, symbols, edges, and reports
- Redis for webhook idempotency and task queue coordination
- Qdrant for repository memory
- Ollama for pluggable local LLM and embedding providers

Environment variables can override defaults from `src/core/config.py`:

- `DATABASE_URL`
- `REDIS_URL`
- `QDRANT_URL`
- `OLLAMA_URL`
- `LLM_MODEL`
- `EMBEDDING_MODEL`
- `ENVIRONMENT`

## Development Checks

Every change should pass:

```powershell
ruff check
mypy
pytest
```

The current workspace uses Python 3.13+ and Pydantic v2.

## Architecture Rules

The project constitution lives in `agents.md` and is authoritative. In short:

- Repository intelligence must work without an LLM.
- Parsing and symbol resolution must be deterministic.
- Agents consume assembled context; they do not retrieve directly.
- Recommendations require evidence, reasoning, impact, and a concrete recommendation.
- Models and embedding providers must remain replaceable.
