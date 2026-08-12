# Nexus Backend

FastAPI app for the Nexus personal knowledge search engine.

## Setup

```bash
uv sync
```

## Run dev server

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: <http://127.0.0.1:8000/api/v1/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

## Test

```bash
uv run pytest -q
```

## Lint and format

```bash
uv run ruff check .
uv run ruff format .
```

## Layout

```
app/
  main.py              FastAPI app factory
  core/
    config.py          pydantic-settings configuration
  api/
    deps.py            shared dependencies
    v1/
      router.py        v1 router aggregator
      health.py        GET /api/v1/health
tests/
  test_health.py       health endpoint test
```
