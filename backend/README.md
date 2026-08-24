# Nexus Backend

FastAPI app for the Nexus personal knowledge search engine.

## Stack

- Python 3.13 (managed by `uv`)
- FastAPI + uvicorn
- SQLAlchemy 2.0 (async, asyncpg driver) + Alembic migrations
- PostgreSQL 17 (native install for now; Docker Compose arrives in Phase 7)
- pydantic-settings for config
- pytest + pytest-asyncio + httpx (AsyncClient) for tests
- ruff for lint + format

## Setup

```bash
uv sync
```

Provision the local Postgres database (one-time):

```sql
-- as the postgres superuser
CREATE ROLE nexus LOGIN PASSWORD 'nexus_dev_pw';
CREATE DATABASE nexus OWNER nexus;
```

Copy the environment template and edit if needed:

```bash
cp .env.example .env
```

Apply migrations:

```bash
uv run alembic upgrade head
```

## Run dev server

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: <http://127.0.0.1:8000/api/v1/health> — returns `{status, env, version, db}`
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

## Migrations

Alembic config lives in `alembic.ini`; migrations in `migrations/versions/`.
The DB URL is read from `Settings.database_url_sync` in `migrations/env.py` —
single source of truth for the connection string.

```bash
uv run alembic revision -m "describe change"   # create empty revision
uv run alembic revision --autogenerate -m "..."  # diff against Base.metadata
uv run alembic upgrade head                    # apply all
uv run alembic downgrade -1                    # roll back one
```

## Layout

```
backend/
  app/
    main.py              FastAPI app factory + lifespan
    core/
      config.py          pydantic-settings configuration (incl. database_url)
    db/
      base.py            SQLAlchemy DeclarativeBase for all models
      session.py         AsyncEngine + sessionmaker + get_db dependency
    api/
      deps.py            shared FastAPI dependencies
      v1/
        router.py        v1 router aggregator
        health.py        GET /api/v1/health (returns db ping status)
  migrations/
    env.py               Alembic env (sync engine, reads from Settings)
    script.py.mako
    versions/            individual revisions
  alembic.ini
  pyproject.toml         deps + ruff + pytest config
tests/
  conftest.py            shared fixtures (async HTTP client)
  test_db.py             /health, SELECT 1, Alembic layout sanity
```
