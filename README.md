# Nexus

> A personal search engine for your own documents. Upload PDFs, DOCX, and TXT files; find them again later by keyword.

![Phase 2 — MVP complete](https://img.shields.io/badge/phase_2-MVP_complete-2ea44f)
![Backend tests](https://img.shields.io/badge/backend_tests-113_passing-blue)
![License](https://img.shields.io/badge/license-TBD-lightgrey)

---

Nexus is a private search engine for personal documents. You upload files, it extracts the text and indexes it, and you can run keyword search across everything in your library. It's not a generic "AI PDF chatbot" — it's a serious backend-heavy engineering project covering databases, full-text search, async processing, authentication, testing, and clean service architecture.

This repo is the Phase-2 MVP build. The current state is **functional end-to-end**: register → upload → text extracted → keyword search → view results, with a thin Next.js UI driving the whole thing. Phase 7 will productionize it; Phase 8 adds advanced features.

---

## Why this project

I built Nexus to cover the breadth of a real backend stack end-to-end, in one project, without skipping steps:

- **A real relational database** (PostgreSQL), not a JSON file
- **A real authentication system** (argon2id + JWT), not a single hard-coded password
- **A real search engine** (Postgres FTS with a `tsvector` generated column + GIN index), not grep
- **A real upload pipeline** (streaming, content-hashed, atomically written), not a one-shot `read()`
- **A real test suite** (113 backend tests, async + integration + edge cases)
- **A real frontend** (Next.js + TanStack Query, with auto-refresh on token expiry)

Everything is wired to a real Postgres instance running locally; nothing is mocked.

---

## Features (Phase 2 — MVP)

**Auth.** Email + password (argon2id), HS256 JWT with 15-minute access and 7-day refresh tokens, same `401 invalid credentials` body for unknown-email and wrong-password (no user enumeration), 403 for disabled accounts, race-safe duplicate-email detection.

**Upload.** Authenticated multipart upload streamed through a `SpooledTemporaryFile`, sha256-computed incrementally, size-capped at 100 MiB (enforced mid-stream), filenames sanitized (path traversal rejected, null bytes stripped, length capped). Storage key is `<owner_uuid>/<doc_uuid>.<ext>`; writes are atomic via `tempfile.mkstemp` + `os.fsync` + `os.replace`.

**Text extraction.** PDF (pypdf), DOCX (python-docx), TXT (stdlib UTF-8). Failure is non-fatal: row gets `status=failed` and `extracted_text=null`, file stays on disk for retry.

**Dedup.** Per-owner `UNIQUE (owner_id, sha256)` constraint with service-layer pre-check and race-condition fallback. Uploading the same file twice returns the existing `DocumentPublic`; only one file lives on disk.

**Search.** Postgres full-text search over `extracted_text` with a GENERATED `tsvector` column (English config) and a GIN index. `plainto_tsquery` for safe user input, `ts_rank` ordering, owner-scoped. Returns slim `DocumentSearchHit` rows; full content via `GET /api/v1/documents/{id}` (404 for cross-user).

**Frontend.** Next.js 16 App Router + TypeScript + Tailwind v4 + TanStack Query. Register → upload → search → view document, all wired to the backend with bearer-token auth and one-shot auto-refresh on 401.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind v4 + TanStack Query | App Router with server components by default; SSR-capable; TanStack for cache + invalidation primitives |
| Backend | Python 3.13 + FastAPI | Async-first, auto OpenAPI from type hints, best ML ecosystem for later embedding work |
| Database | PostgreSQL 17 (asyncpg driver) | One engine for relational, full-text (`tsvector` + GIN), and (later) vectors via `pgvector`. Avoids running ElasticSearch for a single user |
| ORM | SQLAlchemy 2.0 async + Alembic | Typed `Mapped[T]` / `mapped_column`; async sessions; autogenerate for table migrations, hand-written for extensions |
| Auth | argon2-cffi + PyJWT | OWASP-recommended Argon2id (memory-hard); HS256 JWTs with short access window |
| Search | PostgreSQL FTS (built-in) | `to_tsvector` + `plainto_tsquery` + GIN index. No external service. |
| Storage | Local disk (Phase 7 → S3-compatible) | `Storage` Protocol with `put_file_obj` for streaming. Atomic writes via `tmp + os.replace`. |
| Tests | pytest + pytest-asyncio + httpx.AsyncClient | Shared event loop scope keeps asyncpg's pool consistent across tests |
| Tooling | `uv` (not pip), `ruff` (lint + format), Alembic | uv: 10–100× faster than pip + lockfile reproducibility. ruff: replaces flake8 + isort + black in one tool. |

---

## Architecture

```
Frontend (Next.js — http://localhost:3000)
        │
        ▼  HTTP/JSON + Bearer token
API (FastAPI — http://127.0.0.1:8000)
   │
   ├── auth/         register · login · refresh · me
   ├── documents/    POST (upload) · GET /{id}
   └── search/       GET ?q=&limit=
        │
        ▼
PostgreSQL 17 (nexus / nexus DB on localhost:5432)
   ├── users          uuid PK · citext email · argon2id hash · is_active · timestamps
   ├── documents      uuid PK · FK owner_id CASCADE · filename · mime · size · sha256 ·
   │                  storage_path · status enum · extracted_text · search_vector (GENERATED tsvector)
   └── alembic_version
        │
        ▼
Local disk (./var/documents/<owner_uuid>/<doc_uuid>.<ext>)
```

---

## Getting started

### Prerequisites

- Python 3.13 (or use `uv` which manages this for you)
- Node 24+ for the frontend
- PostgreSQL 17 reachable on `localhost:5432`

### Backend

```bash
cd backend
uv sync                                              # install
cp .env.example .env                                  # then edit DATABASE_URL if needed
uv run alembic upgrade head                          # apply all migrations
uv run uvicorn app.main:app --reload --port 8000     # dev server
```

Verify: `curl http://127.0.0.1:8000/api/v1/health` returns `{status: "ok", db: true}`.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local                      # edit NEXT_PUBLIC_API_BASE if needed
npm run dev                                           # → http://localhost:3000
```

---

## Usage walkthrough

Once both servers are running, in the browser:

1. Open <http://localhost:3000> → click **Get started** → register an account.
2. You're auto-redirected to `/app` (upload + search side-by-side).
3. Pick a PDF / DOCX / TXT (e.g. `backend/tests/fixtures/sample.pdf`) and click **Upload**. A green confirmation shows the new document.
4. Type **"Hello"** in the search box and click **Search**. Hits appear with filename, mime, size, and rank.
5. Click a hit → a modal opens with the document's metadata + extracted text.
6. Try uploading the **same file again** — you'll get the existing document back, no duplicate row, no extra file on disk.

---

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/v1/health` | — | Health + DB ping |
| POST | `/api/v1/auth/register` | — | Create user, return tokens |
| POST | `/api/v1/auth/login` | — | Authenticate, return tokens |
| POST | `/api/v1/auth/refresh` | — | Exchange refresh for new tokens |
| GET | `/api/v1/auth/me` | Bearer | Current user info |
| POST | `/api/v1/documents` | Bearer | Multipart upload, returns `DocumentPublic` 201 |
| GET | `/api/v1/documents/{id}` | Bearer | Full `DocumentPublic` (404 for cross-user) |
| GET | `/api/v1/search` | Bearer | `?q=&limit=` → slim `DocumentSearchHit` list |

Interactive docs at <http://127.0.0.1:8000/docs> (Swagger) and `/redoc`.

---

## Testing

```bash
cd backend
uv run pytest -q        # 113 tests, ~5s
uv run ruff check .      # lint
uv run ruff format --check .   # format check
```

113 tests across 9 files, including unit, integration, and edge cases:

- **Auth & sessions** — registration, login, refresh, `/me`; JWT claim shape; enumeration-prevention; disabled-account handling; signature-tampering rejection; wrong-secret rejection.
- **ORM & schema** — User + Document round-trips, FK constraints, cascade delete with owner, Pydantic schema validation against ORM instances.
- **Storage** — `LocalDiskStorage` round-trips, atomic writes via `tmp + os.replace`, path-traversal rejection, binary payload safety.
- **Upload pipeline** — auth, size cap (413), filename sanitization, extension dispatch, hash verification, dedup via `(owner_id, sha256)`, race-condition fallback.
- **Text extraction** — PDF (pypdf), DOCX (python-docx), TXT (stdlib); corrupted input handling; case-insensitive extension dispatch.
- **Search** — Postgres FTS via GENERATED `tsvector` + GIN, `plainto_tsquery` safety, `ts_rank` ordering, owner scoping, get-by-id cross-user 404.

---

## Engineering decisions worth highlighting

- **Service layer + thin routes.** Business logic lives in `app/services/` (pure async, no FastAPI imports). Routes parse, dispatch, and translate exceptions to HTTP. The split lets business logic be unit-tested without spinning up a server.
- **Thin `AuthProvider` handshake.** Tokens-in-localStorage + React state are two sources of truth. After a successful login, the form explicitly calls `signIn()` on the AuthContext — otherwise `/app`'s guard effect (which reads `useAuth().authenticated`) bounces the user back to `/login`, despite valid tokens. Two-line bug, easy to ship without noticing.
- **Streaming upload.** `SpooledTemporaryFile(1 MiB)` holds chunked upload bytes in memory or on disk; `LocalDiskStorage.put_file_obj` streams them to the target via the same atomic `tmp + fsync + os.replace` as in-memory `put()`. A 100 MiB upload peaks at ~1 MiB of memory, not 100.
- **Postgres GENERATED tsvector.** No app code keeps the search index in sync. Postgres computes the `tsvector` from `extracted_text` automatically; the GIN index covers it. `plainto_tsquery` over `to_tsquery` because user input is untrusted (no special-char crashes).
- **Duplicate detection: belt + suspenders.** Service-layer pre-check for the common case (fast, clean); UNIQUE `(owner_id, sha256)` for the race (rare). Either path: clean up the just-written file and return the existing row. Per-owner, not global — two users can both keep the same public PDF in their own libraries.

---

## Project layout

```
backend/
  app/
    api/                    FastAPI routes + shared deps
    core/                   config + auth primitives
    db/                     engine, session, base
    models/                 SQLAlchemy ORM (User, Document)
    schemas/                Pydantic request/response shapes
    services/               business logic (no FastAPI imports)
    storage/                blob storage abstraction
    main.py                 FastAPI factory + lifespan + CORS
  migrations/               Alembic
  tests/                    113 tests + commited binary fixtures
frontend/
  app/                      Next.js App Router pages
  components/               auth-form, upload-form, search-box, ...
  lib/                      api client, auth context, types
notes/                      personal tracking (gitignored)
```

---

## Roadmap

- [x] **Phase 1 — Foundation**
- [x] **Phase 2 — MVP** (auth, upload, text extraction, basic keyword search, frontend)
- [ ] Phase 3 — Search Engine: ranking tuning, filters, pagination, snippets, faceting
- [ ] Phase 4 — Semantic Search: embeddings, `pgvector`, similarity search
- [ ] Phase 5 — Hybrid Search: RRF combiner, score normalization
- [ ] Phase 6 — Background Processing: Redis + Celery, async ingestion, retries
- [ ] **Phase 7 — Production Engineering** ← the resume-worthy milestone
- [ ] Phase 8 — Advanced Features: dedup (deep), versioning, code search, knowledge graph, OCR

---

## License

TBD. Will be chosen before the repo goes public.

---

## Author

**Levin** — [github.com/Levin0908](https://github.com/Levin0908)
