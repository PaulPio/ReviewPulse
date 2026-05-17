# ReviewPulse

Author intelligence on book reviews: ingest fixture or dataset-backed reviews, analyze with an LLM via **OpenRouter** (OpenAI-compatible SDK), store **pgvector** embeddings for semantic search, and explore trends in a small React dashboard.

## Quick start (under 10 minutes)

1. **Prerequisites:** Python 3.12+, Node 20+, Docker Desktop.

2. **Start Postgres + Redis**

   ```bash
   docker compose up -d
   ```

   Postgres is exposed on **localhost:5433** (avoids clashing with a local Postgres on 5432). To reset the DB completely: `docker compose down -v && docker compose up -d`.

3. **Backend**

   ```bash
   cd backend
   python -m pip install -e ".[dev]"
   cp ../.env.example ../backend/.env   # optional; defaults match docker-compose
   python -m alembic upgrade head
   ```

4. **Optional seed (author + two books with demo ASINs)**

   ```bash
   python ../scripts/seed_dev.py
   ```

   Copy the printed UUID into the dashboard or `X-Dev-Author-Id` header.

5. **API server**

   ```bash
   cd backend
   set DEV_AUTH_BYPASS=true
   python -m uvicorn app.main:app --reload --port 8000
   ```

6. **Worker (ingestion / analysis)**

   From **`backend/`** (same folder as `app/`). Use **`python -m celery`** so you don’t rely on the `celery.exe` shim being on PATH (common issue on Windows).

   **Bash:**

   ```bash
   cd backend
   export DEV_AUTH_BYPASS=true
   export USE_MOCK_LLM=1
   python -m celery -A app.celery_app worker --loglevel=INFO
   ```

   **PowerShell / cmd:** use `set DEV_AUTH_BYPASS=true` and `set USE_MOCK_LLM=1` instead of `export`.

   For real OpenRouter calls, set `OPENROUTER_API_KEY` and unset `USE_MOCK_LLM`.

   **Beat (optional, hourly re-ingest):** `python -m celery -A app.celery_app beat --loglevel=INFO`

   If the worker errors connecting to Redis, run `docker compose up -d` and check `CELERY_BROKER_URL` in `backend/.env`.

7. **Frontend**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Open http://localhost:5173 — Vite proxies `/api` → `http://127.0.0.1:8000`.

## Environment

See [.env.example](.env.example). Important keys:

- `DATABASE_URL` — Postgres + pgvector (Supabase in production: enable the `vector` extension).
- `OPENROUTER_API_KEY` — chat + embeddings models (`OPENROUTER_MODEL_ANALYSIS`, `OPENROUTER_MODEL_EMBEDDING`).
- `DEV_AUTH_BYPASS=true` — local only; authenticate with `X-Dev-Author-Id: <author-uuid>`.
- `SUPABASE_JWT_SECRET` — required for `POST /api/v1/auth/bootstrap` with a real Supabase access token (`aud=authenticated`).
- `WEBHOOK_SIGNING_SECRET` / `WEBHOOK_DELIVERY_URL` — optional outbound HMAC webhook after ingest jobs.
- `WEBHOOK_INGESTION_SECRET` — optional separate secret for **inbound** `POST /api/v1/webhooks/ingestion` (defaults to signing secret if empty).

## Real dataset import

After you have a `book` row (from the UI or seed), import JSON/CSV reviews:

```bash
python scripts/import_reviews.py --book-id <uuid> --file path/to/reviews.json
```

JSON accepts `reviews: [...]`, a bare list, or the same `items` shape as `sample_reviews.json`. CSV columns: `external_key`, `body`, optional `rating`, `review_date` / `unixReviewTime`. Cite UCSD / Kaggle sources in your write-up (see **Dataset notes**).

## Webhook (N10)

### Outbound (after ingest)

Payloads are JSON bytes. Header:

`X-ReviewPulse-Signature: sha256=<hex>`

where `<hex>` = HMAC-SHA256(secret, raw_body). Verify (Python):

```python
import hashlib, hmac, json
body = json.dumps(payload).encode()
expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, request.headers["X-ReviewPulse-Signature"])
```

### Inbound (trigger ingest)

`POST /api/v1/webhooks/ingestion` with the **same** signature scheme and JSON body:

```json
{ "book_id": "<uuid>", "idempotency_key": "optional-stable-key" }
```

Uses `WEBHOOK_INGESTION_SECRET` if set, otherwise `WEBHOOK_SIGNING_SECRET`. Returns `503` if no secret is configured. No `X-Dev-Author-Id` required — integration tests cover HMAC validation.

## Tests

With **Docker Compose** running (`docker compose up -d`), the suite creates `reviewpulse_test` automatically if missing, enables `vector`, and runs integration + API tests:

```bash
cd backend
python -m pytest tests/ -q
```

Without Postgres, **mock-LLM unit tests** still run; DB-backed tests are **skipped** with a message pointing at `docker compose up -d`.

For unit tests only (no DB):

```bash
cd backend
python -m pytest tests/test_mock_llm.py -q
```

## Dataset notes (assignment)

- **Synthetic / fixture:** `backend/app/data/sample_reviews.json` keyed by ASIN (`DEMOASIN01`, …).
- **Public corpora (cite in your writeup):** UCSD Amazon Review Data (McAuley lab), SNAP Amazon reviews, or Kaggle book-review samples — import via your own script into `books` / `reviews`.

## Product instinct (P1)

**Editor export pack:** `GET /api/v1/books/{id}/export.csv` returns themed quotes (snippet, sentiment, themes). The dashboard **Book** tab includes a download button (auth header preserved via `fetch`).

## Performance note (N1)

- **Warm path:** ingest + analyze + embed is bounded mainly by OpenRouter latency and Celery throughput; target “ISBN → dashboard useful” under ~60s once workers and DB are warm.
- **Cold path:** Vercel static, Render/Fly API sleep, and managed Postgres wake can add tens of seconds — document those separately from pipeline timing in submissions.

## Deploy shape (free tiers)

- **Frontend:** Vercel static hosting (`frontend` `npm run build` → `dist/`).
- **API + Celery:** Render / Fly.io / Railway (long-lived worker + Redis).
- **DB:** Supabase Postgres with `vector` enabled. Disable `DEV_AUTH_BYPASS` in production; rotate all webhook secrets.

## What we’d extend next

- Supabase Auth end-to-end (replace dev header).
- Stronger ingestion from real datasets / APIs with stable external keys (idempotent F11).
- Richer dashboard charts; stricter theme filters in SQL.
