# ReviewPulse Architecture

## System Diagram

```
┌──────────────┐     ┌──────────────────────────────────────────┐
│   Frontend   │     │              Backend (FastAPI)            │
│  React+Vite  │────▶│  /api/v1/books, reviews, search, etc.   │
│   (Vercel)   │     │                                          │
└──────────────┘     └──────────┬───────────────┬───────────────┘
                                │               │
                     ┌──────────▼──┐   ┌────────▼────────┐
                     │  PostgreSQL  │   │     Redis       │
                     │  + pgvector  │   │  (broker/cache) ���
                     │  (Supabase)  │   └────────┬────────┘
                     └─────────────┘            │
                                       ┌────────▼────────┐
                                       │  Celery Worker   │
                                       │  - Ingest tasks  │
                                       │  - Analyze tasks │
                                       │  - Embed tasks   │
                                       └────────┬────────┘
                                                │
                                       ┌────────▼────────┐
                                       │  LLM Providers   │
                                       │  - OpenRouter    │
                                       │  - OpenAI direct │
                                       └─────────────────┘
```

## Data Flow

1. **Ingestion**: Author adds book → API creates Job → Celery loads reviews from seed/source → stores in DB
2. **Analysis**: Celery picks up unanalyzed reviews → calls LLM (sentiment, themes, AI-detection) → updates review rows
3. **Embedding**: Celery generates vector embeddings → stores in pgvector column
4. **Query**: Frontend requests analytics → API aggregates from DB → returns trends/metrics
5. **Search**: User enters natural language query → API embeds query → pgvector cosine similarity → returns ranked results

## Multi-Tenant Isolation

Every data table has `author_id` as a foreign key. Three layers of defense:

1. **API Layer**: `get_current_author` dependency extracts author from JWT; all queries filter by it
2. **Query Layer**: Every SELECT includes `WHERE author_id = :current_author_id`
3. **Database**: Unique constraints prevent cross-tenant data collisions

## LLM Provider Abstraction

The `LLMProvider` protocol defines a `analyze_review()` method. Two implementations exist:
- `OpenRouterProvider`: Primary. Uses OpenRouter gateway (single API key, cheapest models)
- `OpenAIProvider`: Fallback. Direct OpenAI API with JSON mode

Providers are tried in sequence with fallback on failure. This satisfies the requirement for provider-agnostic LLM usage.

## Async Processing (Celery)

Why Celery over FastAPI background tasks:
- Proper retry with exponential backoff
- Job progress tracking via DB (not lost on process crash)
- Rate limiting per-provider
- Scheduled re-ingestion via Celery Beat
- Scales horizontally by adding workers

## Key Trade-offs

| Decision | Rationale |
|----------|-----------|
| HNSW over IVFFlat | Better recall for continuous inserts, no retraining |
| `ARRAY(Float)` for embeddings | Simpler than raw pgvector in initial implementation |
| Synthetic seed data | Deterministic demo, no external download required |
| HS256 JWT (self-issued) | Simpler than Supabase RS256 for initial build |
| Celery over async tasks | Proper job queue with retries and monitoring |

## What I'd Change With More Time

- Use native pgvector `vector` type instead of `ARRAY(Float)` for proper HNSW indexing
- Add Supabase Auth RS256 validation (currently self-issued HS256)
- Implement proper streaming for LLM responses
- Add WebSocket for real-time job progress (instead of polling)
- Per-author rate limiting with Redis sliding window
- Separate embedding service with batching
