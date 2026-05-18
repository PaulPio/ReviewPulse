# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# Start infrastructure (PostgreSQL + Redis)
docker-compose up -d db redis

# Activate virtualenv (Windows)
cd backend && .venv\Scripts\activate

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000

# Seed database
python scripts/seed_data.py

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Run all tests (requires reviewpulse_test DB to exist)
cd backend && pytest tests/ -v

# Run a single test file
pytest tests/test_api_books.py -v

# Run a single test
pytest tests/test_api_books.py::test_create_book -v
```

### Frontend

```bash
cd frontend && npm install
npm run dev       # http://localhost:5173
npm run build     # tsc + vite build
```

### Test database setup

```bash
createdb reviewpulse_test
```

Tests use a real PostgreSQL DB (`reviewpulse_test`) — never mocked. Each test wraps in a SAVEPOINT that is always rolled back. The test URL is derived automatically from `DATABASE_URL` in `.env`.

## Architecture

### Backend (`backend/app/`)

**FastAPI async application** with SQLAlchemy 2.0 async + PostgreSQL.

- `main.py` — app factory, CORS, lifespan (DB pool dispose on shutdown)
- `core/config.py` — `Settings` (pydantic-settings), cached via `@lru_cache`. All config via env vars / `.env`.
- `api/deps.py` — `get_current_author()`: decodes JWT, fetches `Author` from DB. All protected routes use this as a `Depends`.
- `api/router.py` — registers all sub-routers under `/api/v1`
- `db/base.py` — async engine, `AsyncSessionLocal`, `get_db` dependency
- `models/` — SQLAlchemy ORM: `Author`, `Book`, `Review`, `IngestionJob`, `LLMUsage`, `Webhook`
- `schemas/` — Pydantic request/response models
- `services/analysis.py` — calls LLM, validates response with `AnalysisResult` Pydantic model
- `services/ingestion.py` — loads reviews from seed JSON into DB
- `services/embedding.py` — generates 1536-dim embeddings (default: OpenRouter → `openai/text-embedding-3-small`, or direct OpenAI)
- `services/llm/` — provider abstraction: `base.py` (protocol), `factory.py` (selects primary + fallback), individual clients for `anthropic`, `openai`, `gemini`, `openrouter`
- `tasks/ingestion.py` — Celery task that runs the full pipeline: fetch reviews → LLM analyze → embed → record usage → fire webhook
- `workers/celery_app.py` — Celery app config (Redis broker)

**Multi-tenant isolation**: Every table has `author_id`. The `get_current_author` dependency enforces tenant scoping — every query must filter by `current_author.id`.

### Review embeddings and semantic search

Embeddings are stored as `ARRAY(Float)` (not native pgvector `vector` type — a known limitation). Cosine similarity queries cast at query time: `embedding::vector(1536) <=> '...'::vector(1536)`. This requires the `pgvector` extension to be enabled in PostgreSQL.

### LLM pipeline

Provider selection via `LLM_PROVIDER` env var (default in code: `openrouter`, typical fallback: `openai`). `get_llm_client_with_fallback()` in `factory.py` returns `(primary, fallback | None)`. Analysis service tries primary first, then fallback; individual review failures don't abort the whole job (recorded in `error_details` JSONB on `IngestionJob`).

### Frontend (`frontend/src/`)

React 18 + TypeScript + Vite + Tailwind CSS.

- `App.tsx` — React Router routes; `ProtectedRoute` guards via `useAuth`
- `hooks/useAuth.ts` — JWT stored in localStorage, `getToken()` used by api client
- `lib/api.ts` — thin `fetch` wrapper; reads `VITE_API_URL` env var (defaults to `/api/v1`)
- `hooks/useBooks.ts`, `useReviews.ts`, `useSearch.ts` — React Query hooks
- `pages/` — one file per route: Dashboard, BookDetail, Comparison, Search, Digest, Login, Register
- `components/` — split into `layout/`, `catalog/`, `book-detail/`, `search/`, `ui/`

State management: React Query for server state, Zustand available (in deps) for client state.

### Key env vars

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` async DSN |
| `LLM_PROVIDER` | `anthropic` \| `openai` \| `gemini` \| `openrouter` |
| `LLM_FALLBACK_PROVIDER` | fallback when primary fails |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / etc. | per-provider keys |
| `SECRET_KEY` | JWT signing (HS256) |
| `VITE_API_URL` | frontend API base (defaults to `/api/v1`) |

## Known Limitations / Future Work

- Embeddings use `ARRAY(Float)` instead of native pgvector `vector` type — HNSW index not active
- Auth is self-issued HS256 JWT; Supabase RS256 integration is not complete
- No WebSocket for real-time job progress — frontend polls `/jobs/{id}`
- Celery Beat scheduled tasks exist in `tasks/scheduled.py` but are not wired into production deployment
