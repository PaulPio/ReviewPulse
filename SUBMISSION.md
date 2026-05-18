# ReviewPulse — Take-Home Submission

**Candidate:** Paul Piotrowski  
**Assignment:** ReviewPulse — AI-Driven Book Review Intelligence Platform  
**Submitted to:** Stefan @ Tweeds

---

## What I Built

ReviewPulse is a full-stack, multi-tenant platform that loads book reviews, can run them through an **LLM ingestion pipeline** (sentiment, themes, AI-detection, actionability, embeddings for semantic search), and surfaces intelligence through an author dashboard.

The spec is intentionally larger than 8 hours. I prioritized **multi-tenant API + PostgreSQL + pgvector search + the React flows in the sidebar**, and documented what is **API-only** versus **demo-seeded analysis** versus a **live Celery + provider** path.

---

## Evaluator walkthrough

### What to click (frontend)

All authenticated routes live under the dashboard shell. Sidebar labels map to:

| Sidebar label | Route | What to verify |
|----------------|-------|----------------|
| Catalog | `/` | Stat tiles, What's New, book grid, Add Book |
| Compare | `/compare` | Up to 5 books, sentiment cards, comparison table |
| Search | `/search` | Semantic search, similarity bars on results |
| Digest | `/digest` | Per-book summaries, trend badge, highlights |

Open any book from the catalog: **`/books/:id`** — stat tiles, sentiment timeline, theme breakdown, filterable reviews table.

Auth: **`/login`** and **`/register`**. Demo accounts (password `Demo1234`): `maya@demo.com`, `james@demo.com`, `sarah@demo.com`.

There is **no** Metrics page in the UI; observability is **`GET /api/v1/metrics`** only (see below).

### Live demo (deployed)

| Role | URL |
|------|-----|
| **Frontend** (Vercel) | [https://review-pulse-delta.vercel.app](https://review-pulse-delta.vercel.app) — login: `/login` |
| **API** (Render) | [https://reviewpulse-7mgz.onrender.com](https://reviewpulse-7mgz.onrender.com) |
| **OpenAPI / Swagger** | [https://reviewpulse-7mgz.onrender.com/docs](https://reviewpulse-7mgz.onrender.com/docs) |
| **`VITE_API_URL` used at build** | `https://reviewpulse-7mgz.onrender.com/api/v1` |
| **`CORS_ORIGINS` on Render** | `https://review-pulse-delta.vercel.app` |

### Screenshots (optional)

If helpful for context: assignment brief + sidebar navigation can be attached alongside this document (e.g. exported from Cursor workspace image exports).

### Verification checklist (~45 min call)

1. Register or log in as a demo user.
2. **Catalog** — confirm stats and What's New load; open a book.
3. **Book detail** — charts + reviews table + filters.
4. **Compare** — select multiple books; table updates.
5. **Search** — run a natural-language query; results render.
6. **Digest** — per-book sections render.
7. **Optional API check** — Open [Swagger on prod](https://reviewpulse-7mgz.onrender.com/docs) or `http://localhost:8000/docs` locally; Authorize with JWT from login response; call **`GET /api/v1/metrics`**. Expect pipeline counts for your tenant; **`llm_cost` totals may be zero** unless you have run live ingestion that wrote `LLMUsage` rows (see Demo vs live LLM below).

---

## Working Features

### How to read the tables below

| Layer | Meaning |
|--------|---------|
| **UI** | Exposed in the React app (routes above). |
| **API** | Implemented and reachable under **`/api/v1/...`** (Swagger **`/docs`**); no dedicated dashboard page. |
| **Pipeline** | Celery worker + provider keys + ingest trigger; verifies **live** LLM/embeddings, not the seeded demo labels. |

### Backend API (FastAPI + PostgreSQL + pgvector extension)

Unless noted, paths are relative to **`/api/v1`** (e.g. full URL `http://localhost:8000/api/v1/metrics`).

| Feature | Endpoint | Layer | Notes |
|---------|----------|-------|--------|
| Auth: register, login, JWT | `/auth/register`, `/auth/login`, `/auth/me` | UI + API | |
| Book catalog CRUD | `/books`, `/books/{id}` | UI + API | |
| Paginated review list with filters | `/books/{id}/reviews` | UI + API | Book detail page |
| Sentiment timeline (weekly) | `/books/{id}/trends` | UI + API | |
| Theme frequency breakdown | `/books/{id}/trends/themes` | UI + API | |
| Semantic search via pgvector cast | `/search` | UI + API | Needs embeddings present on reviews |
| Cross-book comparison | `/compare` | UI + API | |
| What's New since last login | `/whats-new` | UI + API | Dashboard card |
| Weekly digest per-book breakdown | `/digest` | UI + API | |
| Audience segment insights (P1) | `/audience-insights` | API | No React page |
| Async ingestion job queue (Celery) | `POST /books/{id}/ingest`, `GET /jobs/{id}`, `GET /jobs` | API | Worker must be running; not wired to a button in the UI |
| Webhook delivery with HMAC signing | `/webhooks` | API | No React page |
| Observability + LLM cost breakdown | `GET /metrics` | API | Response shape: `{ "data": { "pipeline", "llm_cost" } }`. No dashboard UI. Costs/tokens reflect **`LLMUsage`** rows — typically **empty/zero after `seed_db` / synthetic seed only** |

### LLM pipeline (code + tests vs demo vs live)

1. **Implementation** — Provider abstraction with primary + fallback (`LLM_PROVIDER`, `LLM_FALLBACK_*`); Celery task in `app/tasks/ingestion.py` calls analysis + embedding services, records **`LLMUsage`**, updates reviews; per-review failures do not abort the whole job (errors on the job record).
2. **Automated verification** — pytest exercises parsing/fallback behavior with **mocked** LLM responses (`test_analysis.py`, etc.); integration coverage for jobs and isolation (`test_jobs.py`, `test_isolation.py`).
3. **Demo data vs live calls** — `python -m scripts.seed_db` (and the JSON-driven synthetic path) inserts reviews with analysis fields populated from **`target_*` fields in seed JSON**, **without calling providers**. The UI still shows realistic sentiment/themes/charts for grading the dashboard; it does **not** by itself prove a billable LLM run occurred.

**To verify live LLM + metrics costs end-to-end**

1. `docker-compose up -d db redis`
2. Configure `.env`: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, plus provider keys for live calls. Defaults use **OpenRouter** for both LLM and embeddings (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, **`OPENROUTER_API_KEY`** — see `backend/.env.example`). Alternatively set **`OPENAI_API_KEY`** if you point embeddings (or the LLM) at OpenAI directly.
3. `alembic upgrade head`; seed with **`python -m scripts.seed_db`** (or Kaggle seed — same demo accounts).
4. Start API: `uvicorn app.main:app --reload --port 8000`
5. Start worker: `celery -A app.workers.celery_app worker --loglevel=info`
6. Obtain JWT (`POST /api/v1/auth/login`), then **`POST /api/v1/books/{book_id}/ingest`** for a book that has unanalyzed reviews (or add new raw reviews first). Poll **`GET /api/v1/jobs/{job_id}`** until terminal status.
7. **`GET /api/v1/metrics`** — `llm_cost` should reflect accumulated **`LLMUsage`** for that author.

### Multi-tenant isolation

Every table has `author_id`. The `get_current_author` FastAPI dependency is the single enforcement point — every query filters by `current_author.id`. Reviews carry a denormalized `author_id` column so cross-tenant blocking requires no JOINs.

Tested two ways:

1. Structural: inspection of every route handler confirms `current_author` dependency is present  
2. Integration: two author JWTs confirm cross-tenant access is rejected at the API layer

### Frontend dashboard (React + TypeScript + Tailwind)

| Page | Route | What it does |
|------|-------|----------------|
| Login | `/login` | JWT acquisition |
| Register | `/register` | New author |
| Catalog (sidebar) | `/` | Stat tiles, What's New, book catalog, Add Book |
| Book detail | `/books/:id` | Stat tiles, sentiment timeline, theme breakdown, reviews table |
| Compare | `/compare` | Up to 5 books, sentiment cards, metrics table |
| Search | `/search` | Semantic search, similarity score bars |
| Digest | `/digest` | Per-book sentiment summary, trend badge, actionable highlights, AI-flagged alert |

Design language: green/yellow/red sentiment, stat tiles, Recharts for trends, paginated tables for raw reviews.

### Test suite (pytest)

- `test_analysis.py` — LLM mock tests: valid parse, fallback trigger, all-provider failure, invalid JSON handling  
- `test_ingestion.py` — ingestion pipeline integration  
- `test_isolation.py` — structural + integration multi-tenant isolation tests  
- `test_security.py` — auth boundary tests  
- `test_api_books.py` — book CRUD API tests  
- `test_reviews.py` — review filter and pagination tests  
- `test_jobs.py` — Celery job lifecycle tests  

Tests use a real PostgreSQL database (`reviewpulse_test`), not an in-memory substitute — each test wraps in a SAVEPOINT that always rolls back.

### Demo data

- **`python -m scripts.seed_db`** — Creates demo authors/books/reviews; analysis fields come from **seed JSON targets**, not live LLM calls. Fast path for UI demos.  
- **`python -m scripts.seed_kaggle`** — Optional: downloads `mohamedbakhet/amazon-books-reviews`, selects highly reviewed titles, assigns books per demo author, caps reviews per book; **same demo emails** and password `Demo1234`.

Ensure `seed_reviews.json` exists before `seed_db` (run `python scripts/seed_data.py` once if needed).

**Demo accounts** (all password: `Demo1234`):

- `maya@demo.com`  
- `james@demo.com`  
- `sarah@demo.com`  

---

## API Setup

```bash
# 1. Start PostgreSQL + Redis
docker-compose up -d db redis

# 2. Backend
cd backend
python -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env  # fill in API keys for live ingestion when testing pipeline
alembic upgrade head
python -m scripts.seed_db      # demo tenants + synthetic analysed reviews (recommended for UI walkthrough)
# OR: python -m scripts.seed_kaggle   # real Kaggle samples (needs kaggle.json)
uvicorn app.main:app --reload --port 8000

# 3. Celery worker (required only for live POST .../ingest jobs)
celery -A app.workers.celery_app worker --loglevel=info

# 4. Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

Minimum env vars for **API + UI without live ingestion**:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reviewpulse
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=any-random-string
```

Add **`OPENROUTER_API_KEY`** (recommended defaults) or the keys for whichever **`LLM_PROVIDER`** / **`EMBEDDING_PROVIDER`** you select (`backend/.env.example`) when exercising **live** analysis + embedding writes.

---

## Read-only demo deployment (minimal time)

Use this when you need a **public URL** quickly and can skip async ingestion. **Redis and Celery are not required** if nobody calls `POST /books/{id}/ingest`.

### What to provision

| Piece | Purpose |
|--------|---------|
| Managed **PostgreSQL** with **pgvector** enabled | Primary datastore + similarity operator |
| One **API** process | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (platform sets `$PORT` on many hosts) |
| Static **frontend** (e.g. Vercel / Netlify / Cloudflare Pages) | `npm run build` output from `frontend/` |

### Steps

1. Create the database; enable the **pgvector** extension (provider docs vary).
2. Set **`DATABASE_URL`** (async: `postgresql+asyncpg://…`), **`SECRET_KEY`**, and **`CORS_ORIGINS`** / equivalent so your **frontend origin** is allowed (see [`backend/app/core/config.py`](backend/app/core/config.py) — localhost defaults are not enough in production).
3. Deploy or run the API; on first deploy run **`alembic upgrade head`** against prod (release command or one-off shell).
4. **Seed once** from a trusted machine with prod `DATABASE_URL`:  
   `cd backend && python -m scripts.seed_db`  
   (ensure `data/seed_reviews.json` exists — run `python scripts/seed_data.py` first if needed.)
5. Build the frontend with **`VITE_API_URL`** set to your **public API base**, including `/api/v1`. **This deployment:** `https://reviewpulse-7mgz.onrender.com/api/v1`. Set **`CORS_ORIGINS`** on Render to the Vercel origin: `https://review-pulse-delta.vercel.app`. Production does not use the Vite dev proxy in [`frontend/vite.config.ts`](frontend/vite.config.ts).

### Deployed URLs (reference)

Same as [Live demo (deployed)](#live-demo-deployed) above: frontend **https://review-pulse-delta.vercel.app**, API **https://reviewpulse-7mgz.onrender.com**.

### What works vs what does not (honest)

- **Works:** Login/register, catalog, book detail (charts + reviews), compare, digest, what’s new — seeded reviews carry analysis fields from JSON targets.
- **Does not run without Redis + worker:** `POST /books/{id}/ingest`, Celery-backed jobs.
- **Semantic search:** The `/search` path only surfaces rows with non-null **`embedding`**. `seed_db` / current seed scripts **do not** populate embeddings, so **Search may return no rows** until embeddings exist (e.g. live ingestion with **`OPENROUTER_API_KEY`** / configured embedding provider, or a one-off embed job). Say so in the demo if asked.

### Full stack later

Add **Redis**, a **Celery worker** process (same codebase, worker command), and provider keys when you want live ingestion and metrics cost rows — same as the local “API Setup” worker step above.

---

## What's Not Complete

| Item | Why deferred |
|------|-------------|
| Metrics / LLM observability **dashboard page** | **`GET /metrics`** returns JSON only; no React route or sidebar link |
| End-to-end LLM demo **without setup** | Demo seeds **do not** invoke providers; verifying real tokens/cost requires worker + keys + `POST /books/{id}/ingest` |
| Native pgvector `vector` column type | Using `ARRAY(Float)` with runtime `::vector(1536)` cast; HNSW index inactive |
| Supabase Auth RS256 | HS256 JWT is the active path |
| WebSocket job progress | Frontend polls `/jobs/{id}`; WebSocket not implemented |
| Email delivery for digest | Digest API preview only; no SendGrid/Resend |
| Production deployment | **Live:** [review-pulse-delta.vercel.app](https://review-pulse-delta.vercel.app) + [reviewpulse-7mgz.onrender.com](https://reviewpulse-7mgz.onrender.com). No `render.yaml` in-repo; SPA rewrites live in [`frontend/vercel.json`](frontend/vercel.json). **Read-only demo deploy playbook** is documented above |

---

## Time Breakdown (~11 hours total)

Rough split: **~8 hours** on the take-home itself (planning through polish), plus **~3 hours** getting the **live** stack wired — **Vercel** (frontend), **Render** (API), and **Neon** (Postgres + pgvector).

**~1 hour — Planning with Claude Code**  
Worked through the spec iteratively with Claude as a planning partner. This is where I mapped out the full architecture, identified the multi-tenant isolation pattern, chose the LLM provider abstraction design, and laid out the component hierarchy for the frontend. The plan document still lives in `.claude/plans/`.

**~1 hour — Core architecture**  
Database models, SQLAlchemy async setup, Alembic migrations, FastAPI app factory, JWT auth dependency, Celery app config, and the LLM provider protocol + factory. Everything the rest of the project depends on.

**~6 hours — Building, testing, debugging**  
This is where the real time went. The main friction points:

- The pgvector `double precision[] <=> vector` type error — PostgreSQL requires an explicit `::vector(1536)` cast on the `ARRAY(Float)` column before the cosine similarity operator will accept it  
- SQLAlchemy 2's `Row` doesn't expose aliases from `text("...AS alias")` — had to switch to `literal_column("...").label("alias")` for reliable attribute access  
- The digest and what's-new endpoints were wrapping their response in `{ "data": { ... } }` while every other endpoint returned data directly — the frontend was silently receiving the wrong shape  
- Getting Recharts to respect CSS variables for colors and borders took more iteration than expected  

**~3 hours — Deploying the public demo**  
After everything worked locally, standing up the hosted path took longer than I expected. Coordinating **two deploy targets** (static SPA + long-running API), **`VITE_API_URL` at build time**, **`CORS_ORIGINS`**, Neon **`DATABASE_URL`** / TLS (`asyncpg` vs libpq query params), migrations + seed against prod, and debugging **500s that showed up as “CORS” in the browser** added real overhead.

I chose **Neon** for the hosted database because I had **hit the limit on free Supabase projects** — Neon stayed within free tier and pgvector worked fine once migrations ran against the right connection string.

---

## Reflection

The biggest lesson from this mini-hackathon: **one-shotting the entire project was less efficient than it would have been to work through it in explicit vertical slices** — auth → one book endpoint → one frontend page → working end-to-end, then repeat.

The way I approached it (plan everything, build everything, then discover integration issues at the end) meant debugging was harder because multiple layers were new at the same time. When the semantic search broke it wasn't obvious whether the issue was the FastAPI route, the SQLAlchemy query, the pgvector cast, or the React Query hook — all four were untested together.

Going slice by slice gives you a working system at every step. Errors are isolated to the one layer you just added. For a spec this size, 8 slices of 1 hour each would have surfaced issues earlier and left more time for polish.

What is **solid for review**: **multi-tenant API boundaries**, **sidebar dashboard flows**, **pgvector-backed search** (with embeddings present), **structured tests**, and **documented API-only surfaces** (metrics, webhooks, audience insights, ingest trigger). What needs **explicit setup** for a **live** LLM story: Celery worker, keys, and ingest — and a **metrics UI** would be the next polish item for parity with the brief's observability narrative.

Looking forward to walking through it on a call.

---

## Stack Decisions Worth Noting

**OpenRouter as LLM gateway** — Single API key, access to many models, cost signals in responses. Swapping models is largely configuration.

**`ARRAY(Float)` vs native `vector` type** — The pgvector Python extension exposes the `vector` SQLAlchemy type, but integrating it into Alembic migrations adds complexity I wasn't willing to take on inside 8 hours. The runtime cast approach (`embedding::vector(1536) <=> '...'::vector(1536)`) works correctly — it just means the HNSW index isn't active. For a dataset of this size, sequential scan is fast enough. Native `vector` column is the right next step.

**Self-issued HS256 JWT over Supabase Auth** — Supabase Auth is the right long-term call (handles refresh tokens, social login, MFA). But integrating RS256 validation against Supabase's JWKS endpoint adds a moving part that could silently break. HS256 with a local `SECRET_KEY` is simpler to reason about and easier to test. The `get_current_author` dependency is the abstraction boundary — swapping the auth backend means changing one function.

**React Query over Redux** — The data in this app is almost entirely server state. React Query's automatic cache invalidation and background refetching handle 90% of the state management without any boilerplate. Local state (filter controls, modal visibility) stays in `useState`. No Zustand needed.
