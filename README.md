# ReviewPulse

AI-driven book review intelligence platform for independent authors. Ingests Amazon-style reviews, analyzes them with LLMs (sentiment, themes, AI-detection, actionability), stores vector embeddings for semantic search, and surfaces the intelligence through a purpose-built analytics dashboard.

Built as a take-home for Tweeds. Stack mirrors Tweeds' production environment: FastAPI + SQLAlchemy 2.0 async + PostgreSQL/pgvector + Celery + React + TypeScript.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 + pgvector (cosine similarity search) |
| Workers | Celery + Redis |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + Recharts |
| Auth | Self-issued JWT (HS256) — Supabase-ready abstraction |
| LLM | **OpenRouter** (default) — also Anthropic, OpenAI, Gemini; primary + optional fallback via env (`LLM_PROVIDER`, `LLM_FALLBACK_PROVIDER`) |
| Embeddings | `text-embedding-3-small` (1536 dims), default via **OpenRouter** (`openai/text-embedding-3-small`) or direct OpenAI |

---

## Local Setup

### Prerequisites
- Python 3.12+ (**avoid 3.14** for installs — many deps lack wheels yet)
- Node.js 18+
- Docker (for PostgreSQL + Redis)
- Kaggle credentials (optional — for real review data)

### 1. Start Infrastructure

```bash
docker-compose up -d db redis
```

### 2. Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — minimum required vars listed below

# Run migrations
alembic upgrade head

# Seed with real Kaggle data (requires ~/.kaggle/kaggle.json)
python -m scripts.seed_kaggle

# Or use synthetic fallback data
# python scripts/seed_data.py

# Start API server
uvicorn app.main:app --reload --port 8000
```

### 3. Celery Worker (async ingestion)

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Minimum Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reviewpulse
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=any-long-random-string

# At least one LLM provider key (defaults use OpenRouter if LLM_PROVIDER unset)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...

# Optional fallback when primary fails (e.g. openai)
LLM_FALLBACK_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Demo Accounts

After running the Kaggle seeder, three demo accounts are available (password: `Demo1234`):

| Email | Books |
|-------|-------|
| `maya@demo.com` | 3 books, ~150 reviews |
| `james@demo.com` | 3 books, ~150 reviews |
| `sarah@demo.com` | 3 books, ~150 reviews |

---

## API Reference

Base URL: `https://reviewpulse-7mgz.onrender.com/docs`

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account, returns JWT |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Current user profile |

### Books

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/books` | Add book to catalog |
| GET | `/books` | List books with aggregated stats |
| GET | `/books/{id}` | Book detail with full stats |
| DELETE | `/books/{id}` | Remove book and all reviews |

### Reviews & Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/books/{id}/reviews` | Paginated reviews with filters |
| GET | `/books/{id}/trends` | Weekly sentiment timeline |
| GET | `/books/{id}/trends/themes` | Theme frequency breakdown |
| POST | `/compare` | Side-by-side book comparison |
| POST | `/search` | Semantic search across all reviews |
| GET | `/whats-new` | Activity since last login |
| GET | `/digest` | Weekly digest per book |
| GET | `/audience-insights` | Reader segment clustering |

### Jobs & Observability

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs/books/{id}/ingest` | Trigger ingestion job |
| GET | `/jobs/{id}` | Poll job status |
| GET | `/jobs` | List all jobs |
| GET | `/metrics` | LLM cost tracking + pipeline stats |
| POST | `/webhooks` | Register webhook (HMAC signed) |
| GET | `/webhooks` | List webhooks |

### Quick Start Example

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"author@example.com","password":"SecurePass1","display_name":"Jane Author"}'

# Add a book (replace <token> with the token from the response above)
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Last Algorithm"}'

# Semantic search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"pacing issues in the middle chapters","top_k":10}'
```

---

## Project Structure

```
ReviewPulse/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, CORS, lifespan
│   │   ├── api/                     # Route handlers (one file per domain)
│   │   │   ├── authors.py           # Auth endpoints
│   │   │   ├── books.py             # Catalog CRUD
│   │   │   ├── reviews.py           # Review list + filters
│   │   │   ├── analytics.py         # Trends, digest, compare, whats-new
│   │   │   ├── search.py            # Semantic search (pgvector)
│   │   │   ├── jobs.py              # Ingestion job polling
│   │   │   ├── webhooks.py          # Webhook CRUD + HMAC
│   │   │   ├── metrics.py           # Cost + observability
│   │   │   └── deps.py              # get_current_author dependency
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── analysis.py          # LLM pipeline orchestration
│   │   │   ├── embedding.py         # Vector embedding generation
│   │   │   ├── ingestion.py         # Review loading from seed data
│   │   │   ├── audience.py          # Reader segment clustering (P1)
│   │   │   └── llm/                 # Provider abstraction
│   │   │       ├── base.py          # Protocol + LLMResponse dataclass
│   │   │       ├── factory.py       # Primary + fallback selection
│   │   │       ├── anthropic.py
│   │   │       ├── openai.py
│   │   │       ├── gemini.py
│   │   │       └── openrouter.py
│   │   ├── tasks/
│   │   │   └── ingestion.py         # Celery task: fetch → analyze → embed → webhook
│   │   └── workers/
│   │       └── celery_app.py
│   ├── tests/
│   │   ├── test_analysis.py         # LLM mock tests (fallback, invalid JSON)
│   │   ├── test_ingestion.py        # Ingestion pipeline integration
│   │   ├── test_isolation.py        # Multi-tenant isolation (structural + integration)
│   │   ├── test_security.py         # Auth boundary tests
│   │   ├── test_api_books.py        # Book CRUD API tests
│   │   ├── test_reviews.py          # Review filter + pagination tests
│   │   └── test_jobs.py             # Celery job lifecycle tests
│   ├── scripts/
│   │   ├── seed_data.py             # Synthetic review generator
│   │   └── seed_kaggle.py           # Real Amazon reviews via Kaggle dataset
│   ├── alembic/                     # DB migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx    # Catalog + stats + What's New
│   │   │   ├── BookDetailPage.tsx   # Charts + filtered review table
│   │   │   ├── ComparisonPage.tsx   # Side-by-side book metrics
│   │   │   ├── SearchPage.tsx       # Semantic search UI
│   │   │   ├── DigestPage.tsx       # Weekly digest per book
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── components/
│   │   │   ├── ui/                  # StatTile, SentimentBar, ScoreBar, Badge, Button…
│   │   │   ├── catalog/             # BookCard, CatalogGrid
│   │   │   ├── book-detail/         # ReviewsTable, SentimentTimeline, ThemeBreakdown
│   │   │   ├── search/              # SemanticSearch
│   │   │   └── layout/              # Sidebar, Header, DashboardLayout
│   │   ├── hooks/                   # React Query hooks (useBooks, useReviews, useSearch…)
│   │   ├── lib/
│   │   │   └── api.ts               # Fetch wrapper, reads VITE_API_URL
│   │   └── types/index.ts           # Shared TypeScript interfaces
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   └── DESIGN.md
├── docker-compose.yml
└── SUBMISSION.md                    # Take-home submission notes
```

---

## Features Implemented

### Core Pipeline
- [x] Multi-tenant book catalog management
- [x] Review ingestion with idempotency (dedup on `external_id`)
- [x] LLM analysis: sentiment + confidence, theme extraction, AI-generation detection, one-sentence summary, actionability flag + reason text
- [x] Provider-agnostic LLM layer — primary + fallback, swap by env var
- [x] Supported providers: Anthropic, OpenAI, Gemini, OpenRouter
- [x] Vector embeddings (1536 dims) for semantic search via pgvector
- [x] Async Celery job queue with progress tracking and error recording
- [x] Webhook delivery with HMAC-SHA256 signatures
- [x] LLM cost tracking per review / book / provider

### Analytics & Dashboard
- [x] Sentiment timeline (weekly, last 12 weeks)
- [x] Theme frequency breakdown (top 10)
- [x] Cross-book comparison table
- [x] Semantic search with similarity score
- [x] "What's New" since last login
- [x] Weekly digest with per-book trend, actionable highlights, AI-flagged alert
- [x] P1: Reader audience segmentation (casual / literary / series fans)

### Security & Quality
- [x] Multi-tenant isolation enforced at the `get_current_author` dependency
- [x] Structural + integration tests confirming cross-tenant access is blocked
- [x] JWT auth with configurable secret
- [x] Structured logging (structlog)
- [x] Pydantic v2 validation on all LLM output

---

## Hosting notes (Render)

Render must use **Python 3.12.x**, not 3.14: newer Python triggers source builds for `pydantic-core` (Rust/maturin) and commonly fails with **read-only file system** during install.

- Service **Root Directory** `backend` picks up [`backend/runtime.txt`](backend/runtime.txt) (`python-3.12.8`).
- Alternatively set Render env **`PYTHON_VERSION`** = `3.12.8`.

Commit `runtime.txt`, redeploy, and confirm build logs show **Python 3.12**, not 3.14.

### Render: build succeeds but **Exited with status 1**

Common causes:

1. **`DATABASE_URL`** — Use **`postgresql+asyncpg://…`** for this app (Neon’s dashboard often copies `postgresql://…`; the backend coerces that automatically, but a wrong driver prefix elsewhere will still break).
2. **TLS to Neon / hosted Postgres** — The API enables **`ssl=True`** for asyncpg automatically when the host looks like Neon (`.neon.tech`), Supabase (`.supabase.co`, `pooler.supabase.com`), or Render Postgres (`postgres.render.com`), or when the URL contains `sslmode=require`. If you ever need to force it on/off, set **`DATABASE_SSL`** = `true` or `false` on Render.
3. **`CORS_ORIGINS`** — Must be full origins with scheme, comma-separated, e.g. `https://review-pulse-delta.vercel.app`. Invalid values can fail validation at startup.
4. **Logs** — Open the service **Logs** tab for the Python traceback (not only the build log).

### Login returns **500** or browser shows **CORS** on `/auth/login`

If the Neon **Tables** UI shows **“0 tables”** in `public`, migrations were never applied to that database — this alone causes login to crash.

**Fix (one-time):** From your machine, point `DATABASE_URL` at the **same** Neon connection string Render uses (pooler URL is fine). Then:

```bash
cd backend
alembic upgrade head
python -m scripts.seed_db   # demo accounts (maya@demo.com / Demo1234) + books + reviews
```

Use `postgresql://` or `postgresql+asyncpg://`; the app normalizes the scheme. Neon often appends `?sslmode=require` — that is fine: the backend removes `sslmode` for asyncpg and turns on TLS via `connect_args`, including **`alembic upgrade head`**. After `upgrade head`, refresh Neon Tables — you should see `authors`, `books`, `reviews`, etc.

**`InvalidPasswordError` / still 0 tables:** Migrations never ran successfully. In **Git Bash**, an unquoted Neon URL breaks at **`&`** (`channel_binding=require` looks like a shell background job — you may see `[1] 5571`). Prefer storing the **full** URI in **`backend/.env`** as `DATABASE_URL=...` (one line) and running `alembic upgrade head` from `backend/` without `export`. Or quote the whole URL: `export DATABASE_URL='postgresql://...require&channel_binding=require'`. Then copy the **same** value into Render. If the password was reset or exposed, use Neon **Reset password** and update every copy.

Often the real failure is **database access** (missing TLS, wrong `DATABASE_URL`, or schema not migrated). The browser may still report **CORS** if the error response does not include expected headers. Fix the traceback in Render logs first. After deploy, confirm startup logs include **`database_ssl=True`** when using Neon. Demo users require **`seed_db`** (or registration) after migrations.

### Browser: **CORS policy** / **Failed to fetch** (Vercel → Render)

The API must allow your frontend **origin**. On **Render** → Web Service → **Environment**, set:

```env
CORS_ORIGINS=https://review-pulse-delta.vercel.app
```

Use the **exact** production URL (scheme + host, **no** path). A trailing slash in the env value is OK — the API strips it so it matches the browser `Origin` header. For extra origins (e.g. preview deploys), use a comma-separated list. **Save**, then **restart/redeploy** the service.

After redeploy, check Render logs for **`cors_allow_origins`** — your Vercel URL should appear **without** a trailing slash. If the list only shows localhost, `CORS_ORIGINS` was empty or misnamed (`CORS_ORIGINS`, not `ALLOWED_ORIGINS`). Also check **`database_ssl`** (boolean): it should be **`True`** when the API is pointed at Neon or similar.

### Vercel: **404** on refresh (`/login`, `/books/…`)

React Router needs every path to serve **`index.html`**. The repo includes [`frontend/vercel.json`](frontend/vercel.json) with an SPA rewrite. Commit it, redeploy Vercel, then hard-refresh or open `/login` again.

If the Render instance was **asleep**, the first API request may return a non-JSON page without CORS headers; wait for wake-up and retry.

---

## Known Limitations / Future Work

| Limitation | Notes |
|-----------|-------|
| `ARRAY(Float)` instead of native `vector` type | Uses runtime `::vector(1536)` cast — works correctly, but HNSW index is not active. Migrating to native `vector` column is the right next step |
| HS256 JWT instead of Supabase RS256 | Auth is self-contained and fully functional. Supabase integration is the right long-term path but adds a moving part |
| No WebSocket for job progress | Frontend polls `/jobs/{id}` every 2 seconds — reliable but not real-time |
| Email delivery for digest | Digest endpoint is fully functional as a preview; wiring to SendGrid/Resend not implemented |
| Deployment | **Live demo:** [review-pulse-delta.vercel.app](https://review-pulse-delta.vercel.app) (frontend) · [reviewpulse-7mgz.onrender.com](https://reviewpulse-7mgz.onrender.com) (API). Playbook: **[Read-only demo deployment](SUBMISSION.md#read-only-demo-deployment-minimal-time)** in `SUBMISSION.md` |

---

## Running Tests

```bash
# Create test database (one time)
createdb reviewpulse_test

# Run all tests
cd backend && pytest tests/ -v

# Run a specific file
pytest tests/test_isolation.py -v

# Run a single test
pytest tests/test_isolation.py::TestIsolationStructure::test_all_routes_require_author -v
```

Tests use a real PostgreSQL test database — never mocked. Each test wraps in a SAVEPOINT that always rolls back.
