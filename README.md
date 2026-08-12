# Nexus

> A personal search engine for your own documents.

## Status

Day 1 of the Foundation phase. Not yet functional. See [Roadmap](#roadmap) for where this is going.

## About

Nexus is a private search engine for personal documents — PDFs, DOCX, Markdown, text files, and (eventually) source code. Upload files, and Nexus extracts, indexes, and lets you search across everything semantically and/or by keyword.

This is **not** a generic "AI PDF chatbot." It is a serious backend-heavy engineering project covering databases, search systems, async processing, authentication, testing, DevOps, and system design.

## Tech Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | Next.js + React + TypeScript + Tailwind + TanStack Query | SSR-capable, typed, great DX |
| Backend | Python + FastAPI | Fast, auto OpenAPI docs, best ML/embeddings ecosystem |
| Database | PostgreSQL + pgvector | One DB for relational data, full-text search, and vectors |
| Search | PostgreSQL FTS first, OpenSearch later if justified | Do not add infra you do not need yet |
| Background jobs | Redis + Celery (or similar) | Decouple slow work from API requests |
| Storage | Local disk first, S3-compatible later | Start simple |
| Infra | Docker, Docker Compose, GitHub Actions | Industry standard |

**Rule:** every technology earns its place by solving a concrete problem in this project.

## Architecture

```
Frontend (Next.js)
        |
        v   HTTP/JSON
API (FastAPI / Python)
   |          |          |
   v          v          v
PostgreSQL   Redis     Object Storage
(+ pgvector) (queue)   (raw files)
                |
                v
            Workers
   (extract -> chunk -> embed -> index)
```

The API does validation and business logic only. Heavy lifting is delegated to workers via Redis.

## Roadmap

- [x] Phase 1 — Foundation: Git, project structure, .gitignore, env config
- [ ] Phase 2 — MVP: Auth, document upload, storage, metadata, basic management, text extraction, basic keyword search
- [ ] Phase 3 — Search Engine: Postgres FTS, ranking, filters, pagination, highlighting, result UI
- [ ] Phase 4 — Semantic Search: Embeddings, pgvector, similarity search
- [ ] Phase 5 — Hybrid Search: Combined ranking, relevance tuning
- [ ] Phase 6 — Background Processing: Redis, queues, workers, async ingestion, retries
- [ ] Phase 7 — Production Engineering: Tests, Docker, Docker Compose, logging, error handling, rate limiting, caching, CI/CD, deployment
- [ ] Phase 8 — Advanced Features: Duplicate detection, versioning, code search, knowledge graph, OCR

## Getting Started

Detailed setup instructions land in Day 2 (Python venv and FastAPI skeleton).

## License

TBD. Will be chosen before the repo goes public.

## Author

Levin — github.com/Levin0908
