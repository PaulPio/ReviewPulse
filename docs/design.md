# Design (ReviewPulse)

## Product goal

Help an indie author answer: **what changed**, **which title is under pressure**, and **what readers keep saying** — without enterprise Amazon tooling.

## Information architecture

| Area        | Purpose |
|------------|---------|
| Catalog    | Card grid with review counts / % negative, ingest, **Open** → Book tab. |
| Book       | Weekly trend list, theme chips, filtered review list (sentiment), export CSV. |
| Search     | Semantic “ask your catalog” (pgvector cosine, tenant-scoped). |
| Compare    | 2–4 titles: sentiment mix, theme frequency, velocity, AI-flag rate. |
| Digest     | Email-width HTML preview of a weekly rollup (no actual send in MVP). |
| Spend      | Honest token + **estimated USD** rollups (startup cost awareness). |

**“What’s new”** uses `last_seen_at` (updated via `POST /api/v1/session/ping`) vs review `created_at` so the feed approximates “since last visit.”

## Visual language

- **Dark zinc base**, **violet accent** for primary actions (not sentiment colors).
- **Sentiment** only: reserve green / amber / red for labels and sparklines later — keep chrome neutral.
- **Density:** compact tables/cards for catalog; generous line-height for review body in future detail view.
- **Typography:** system UI stack; monospace for UUID/ASIN.

## Components (implemented)

- **shadcn-style** primitives: `Button`, `Card`, `Input`, `Badge` (CVA variants), **Radix Tabs** for primary navigation — Tailwind v4 + `cn()` (`clsx` + `tailwind-merge`).
- **lucide-react** icons for section labels.

## Empty / loading / error

- Inline red alert for API errors (FastAPI messages bubble up).
- Catalog empty state explains DEMO ASINs.
- Ingest warns that **Celery** must be running.

## Accessibility

- Buttons have visible labels; forms associate placeholders; future pass: focus rings, aria-live for ingest completion.

## Copy tone

Short, practical, non-marketing — authors are busy; avoid jargon like “embedding” in primary UI (we still expose it in dev-oriented README).
