# Architecture (ReviewPulse)

## Overview

- **API:** FastAPI + SQLAlchemy 2 + Pydantic v2.
- **DB:** Postgres + **pgvector** (one embedding column per review; cosine search scoped by `author_id`).
- **Jobs:** Celery + Redis; Beat schedules hourly re-ingest (`scheduled_refresh_all`).
- **LLM:** **OpenRouter** via OpenAI-compatible Python SDK (`OPENROUTER_*` env). Second implementation: `MockLLMClient` for tests (N2). Swap “provider” by changing model IDs, not code.
- **Web:** React + Vite + TypeScript + Tailwind v4 + Radix **Tabs** + shadcn-style UI primitives; dev proxy to API.

## Multi-tenancy (F12)

- `books.author_id` → `authors.id`. Every query joins through `books` when loading reviews, jobs, spend aggregates, or vector search so **Author B never sees Author A’s rows**.

## Async pipeline

1. `POST /api/v1/books/{id}/ingest` enqueues `run_ingest_job`. Optional **`Idempotency-Key`** header (or webhook body) dedupes per `(author_id, book_id, key)` so retries do not enqueue duplicate work.
2. Worker loads rows from fixture JSON by **ASIN**, upserts `reviews` (`book_id`, `external_key`).
3. For each review without `review_analyses`, calls OpenRouter (or mock) for structured JSON analysis; then embeddings; writes `reviews.embedding`.
4. Terminal job state `completed` / `partial` / `failed`; optional **outbound** HMAC POST to `WEBHOOK_DELIVERY_URL`. **Inbound** `POST /api/v1/webhooks/ingestion` (same HMAC, no user session) can enqueue ingest for a known `book_id` (automation / external schedulers).

## Idempotency (F11)

- Natural key `(book_id, external_key)` unique on reviews.
- Optional **`jobs.idempotency_key`** unique per `(author_id, book_id, idempotency_key)` for ingest job deduplication.
- Skip LLM if `review_analyses` row exists for the review.

## Trade-offs / cuts

- **Fixture ingestion** instead of live Amazon scraping (permitted by spec).
- **Theme filter** via Python on small corpora (fast to ship; SQL JSON operators later).
- **Scheduled job** enqueues ingest for every book hourly — for production, track cursors / diff by `review_date`.
- **N1:** first-run latency depends on worker + OpenRouter; cold free-tier hosts are documented separately from warm-chain time.

## Observability (N12)

- Structured JSON logs via `structlog` in workers and key API failures.
- `GET /api/v1/metrics/summary` surfaces estimated USD + tokens per author (cost table + API usage).

## LLM reliability (N4/N5)

- `OpenRouterClient`: exponential backoff + jitter on 429/5xx (`app/llm/openrouter.py`).
- If JSON or schema validation fails after a chat completion, **one repair round-trip** asks the model to emit valid JSON again (logged at failure site via worker `analyze_failed` if still invalid).

## Cron (F9)

- Celery Beat in `app/celery_app.py` (`reingest-catalog-hourly`). Alternatives: GitHub Actions hitting a secured **inbound webhook**, Vercel/Render cron calling the same, etc.
