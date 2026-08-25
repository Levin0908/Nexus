# Nexus Backend

FastAPI app for the Nexus personal knowledge search engine.

## Stack

- Python 3.13 (managed by `uv`)
- FastAPI + uvicorn
- SQLAlchemy 2.0 (async, asyncpg driver) + Alembic migrations
- PostgreSQL 17 (native install for now; Docker Compose arrives in Phase 7)
- pydantic-settings for config
- argon2-cffi (password hashing) + PyJWT (auth tokens)
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

## Auth

Two endpoints issue access + refresh JWTs.

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"correct-horse-battery-staple"}'

# Login
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"correct-horse-battery-staple"}'
```

Both return `TokenResponse`:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 900
}
```

Tokens are signed HS256 with `JWT_SECRET_KEY` from `.env`. In dev the secret is auto-generated and logged once at startup; in production it must be set or the app refuses to start.

The `/auth/refresh` endpoint and protected-route middleware arrive on Day 6.

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
      config.py          pydantic-settings configuration
      security.py        PasswordHasher (argon2) + JWT create/decode + secret resolver
    db/
      base.py            SQLAlchemy DeclarativeBase for all models
      session.py         AsyncEngine + sessionmaker + get_db dependency
    models/              SQLAlchemy ORM models
      user.py            User table
    schemas/             Pydantic request/response models
      user.py            UserPublic
      auth.py            RegisterRequest, LoginRequest, TokenResponse
    api/
      deps.py            shared FastAPI dependencies
      v1/
        router.py        v1 router aggregator
        health.py        GET /api/v1/health
        auth.py          POST /api/v1/auth/register, /api/v1/auth/login
  migrations/
    env.py               Alembic env (sync engine, reads from Settings)
    script.py.mako
    versions/            individual revisions (init, extensions, users table)
  alembic.ini
  pyproject.toml         deps + ruff + pytest config
tests/
  conftest.py            shared fixtures (async HTTP client, test-user cleanup)
  test_db.py             /health, SELECT 1, Alembic layout sanity
  test_passwords.py      PasswordHasher unit tests
  test_user_model.py     User ORM round-trip + uniqueness + case-insensitive
  test_auth.py           register + login endpoints, JWT claim shape
```
