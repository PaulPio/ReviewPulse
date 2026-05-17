# ReviewPulse

Book review intelligence platform for independent authors. Ingests Amazon-style reviews, analyzes them with LLMs (sentiment, themes, AI-detection), stores embeddings for semantic search, detects trends, and surfaces actionable intelligence through a polished dashboard.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 + pgvector |
| Workers | Celery + Redis |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Auth | Self-issued JWT (HS256) with Supabase-ready architecture |
| LLM | OpenRouter (primary) + OpenAI (fallback) |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |

## Local Setup (< 10 minutes)

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker (for PostgreSQL + Redis)

### 1. Start Infrastructure

```bash
docker-compose up -d db redis
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy env and configure
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY or ANTHROPIC_API_KEY)

# Run migrations
alembic upgrade head

# Generate seed data
python scripts/seed_data.py

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173

### 4. Celery Worker (optional, for async ingestion)

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL async connection string |
| `REDIS_URL` | Yes | Redis URL for Celery broker |
| `SECRET_KEY` | Yes | JWT signing key |
| `OPENAI_API_KEY` | For analysis | OpenAI API key (analysis + embeddings) |
| `ANTHROPIC_API_KEY` | For analysis | Anthropic API key (alternative) |
| `WEBHOOK_HMAC_SECRET` | For webhooks | HMAC signing secret |

## API Overview

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| GET | `/auth/me` | Current user profile |
| POST | `/books` | Add book to catalog |
| GET | `/books` | List books with metrics |
| GET | `/books/{id}` | Book detail |
| GET | `/books/{id}/reviews` | Paginated reviews with filters |
| GET | `/books/{id}/trends` | Sentiment timeline |
| GET | `/books/{id}/trends/themes` | Theme breakdown |
| POST | `/search` | Semantic search |
| POST | `/compare` | Cross-book comparison |
| GET | `/whats-new` | Activity since last login |
| GET | `/digest` | Weekly digest preview |
| GET | `/metrics` | Cost and pipeline metrics |
| POST | `/jobs/books/{id}/ingest` | Trigger ingestion |
| GET | `/jobs/{id}` | Poll job status |
| GET | `/audience-insights` | P1: Reader segments |

### Example: Register + Add Book

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"author@example.com","password":"SecurePass1","display_name":"Jane Author"}'

# Add a book (use token from register response)
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Last Algorithm"}'
```

## Project Structure

```
ReviewPulse/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── api/                 # Route handlers
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── services/            # Business logic
│   │   ├── llm/                 # LLM provider abstraction
│   │   ├── tasks/               # Celery tasks
│   │   └── workers/             # Celery app config
│   ├── tests/                   # pytest tests
│   ├── scripts/seed_data.py     # Data generation
│   ├── alembic/                 # DB migrations
│   └── data/seed_reviews.json   # 202 synthetic reviews
├── frontend/
│   ├── src/
│   │   ├── pages/               # Route pages
│   │   ├── components/          # UI components
│   │   ├── hooks/               # React Query hooks
│   │   └── lib/                 # API client + Supabase
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md          # System design
│   └── DESIGN.md                # UI/UX decisions
└── docker-compose.yml           # Local dev infrastructure
```

## Features Implemented

- [x] Multi-tenant book catalog management
- [x] Review ingestion with idempotency (dedup by external_id)
- [x] LLM analysis: sentiment, themes, AI-detection, actionability
- [x] Provider-agnostic LLM layer (OpenRouter + OpenAI fallback)
- [x] Semantic search via pgvector embeddings
- [x] Sentiment timeline and theme trends
- [x] Cross-book comparison
- [x] "What's New" since last login
- [x] Weekly digest preview
- [x] Webhook delivery with HMAC signatures
- [x] Job queue with progress tracking (Celery)
- [x] Cost tracking per review/book/provider
- [x] P1: Reading Group / Audience Insights
- [x] Multi-tenant isolation (structural + tested)
- [x] Structured logging (structlog)

## What's Not Complete / Future Work

- Supabase Auth RS256 integration (currently self-issued HS256)
- Native pgvector `vector` type (currently using ARRAY(Float))
- Real-time job progress via WebSocket
- Email delivery for weekly digest
- Deployment to Render/Vercel (ready but not deployed)
- Full integration test suite against live DB
