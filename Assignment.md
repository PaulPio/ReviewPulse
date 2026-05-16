Tweeds: Full-Stack Engineering Intern Take-Home

Deadline: 72 hours from the moment you receive this email. Reply with submission before then. Suggested time: 8 hours of coding inside the 72-hour window. We designed the spec so that an experienced engineer can ship something defensible in 8 hours by cutting hard. If you want to spend more, go for it. We respect both: the candidate who ships 60% of the spec in 8 hours with sharp trade-offs, and the candidate who ships 95% in 20 hours because they wanted it. Just don’t fake it. Tell us how long it actually took. Cost: $0 expected. Use free tiers everywhere (Supabase free, Render/Fly.io/Vercel hobby, Anthropic/Gemini/Groq trial credits, GitHub Student Developer Pack if applicable). Reusable: This project is yours. Put it on your resume, on GitHub publicly, talk about it in future interviews. Stack: Choose your own, but you’ll be judged on alignment with how Tweeds builds (see Stack Notes below).

How this is actually evaluated

Both what you ship and how you reason about it matter. The code tells us what you can build; the walkthrough tells us how you think. Either one alone is not enough.

The spec below is intentionally larger than 8 hours of work, even with AI tools. We want to see:

·      What you chose to cut if you stayed in the time-box, and why those cuts were the right ones.

·      What you chose to overdeliver on if you went past it, and why that part deserved your extra hours.

·      Where you took shortcuts, and what you’d do instead with real time.

·      What you noticed about the problem that wasn’t in the spec.

·      How you’d extend it if this were going into production with 1,000 authors next week.

Be honest about hours spent. We grade what you did with the time you took, not the time we suggested.


The problem

Independent authors live and die by Amazon book reviews. A single new review can shift their daily sales by 20-40%. Today they have no way to know what’s happening without manually refreshing their Amazon page or paying for an expensive enterprise tool.

Build ReviewPulse: a small product that gives an author actionable intelligence on the reviews of their books across multiple titles and over time.

The product surface area covers:

1.        Ingestion of the public reviews for an author’s book catalog (multiple books per author).

2.        LLM analysis of each review extracting:

o   Sentiment (positive / mixed / negative) with confidence

o   Themes mentioned (e.g. “pacing”, “characters”, “ending”, “cover”, “narration”)

o   Whether the review is likely AI-generated (flag + confidence 0-1)

o   A one-sentence summary

o   Whether the review is actionable (raises something the author could respond to or fix in next book)

3.        Vector storage so the author can semantically search across all their books (“find reviews mentioning my main character”).

4.        Trend detection. How is sentiment trending week-over-week per book? Which themes are rising or falling?

5.        Comparative analysis. Author has multiple books; dashboard should let them see how reviews differ across titles.

6.        Author dashboard that surfaces:

o   Catalog view (all their books, key metrics at a glance)

o   Per-book deep-dive (reviews list with filters, theme breakdown, sentiment timeline)

o   Cross-book comparison

o   Semantic search across the whole catalog

o   “Weekly digest” preview an author would actually want delivered to their inbox

7.        Background processing. Ingestion + analysis happens async, dashboard never blocks on it.

8.        Scheduled refresh that discovers new reviews and integrates them without duplication.

9.        Multi-tenant data isolation. Author A cannot see author B’s books or reviews. Show the boundary in the schema and API.

10.  A “what’s new since I last logged in” affordance that surfaces the most important review activity since the user’s last visit (whatever you decide that means).

You do not need to scrape Amazon yourself. Two acceptable approaches: - Synthetic mode: generate 100-300 realistic reviews via LLM (structured output, multiple books, multiple authors, multiple timestamps), seed the database, run everything else on top. This is the recommended path. - Real mode: use any third-party reviews API or dataset (Trustpilot/Goodreads/Kaggle Amazon review datasets; there are several free ones). Cite your source.

We care about how you build the system, not whether you have a real Amazon scraper.


Requirements

Functional

·      F1. REST API to register an author, add multiple books to their catalog (URL/ISBN/title), trigger an ingestion job per book.

·      F2. REST API to poll job status (queued / running / completed / failed / partial). Show you understand async, not just await.

·      F3. REST API to list reviews for a book with filters (sentiment, AI-flagged, actionable, theme, date range, pagination, sort).

·      F4. REST API to semantic-search reviews scoped to author’s catalog. Single query, multi-book results. (POST /authors/:id/search { "query": "..." } returns top-K by cosine similarity, with book + review snippet + score.)

·      F5. REST API for trend metrics: sentiment-over-time series per book, theme-frequency-over-time, week-over-week delta.

·      F6. REST API for cross-book comparison: given N book IDs, return a side-by-side view (sentiment distribution, top themes, AI-flagged rate, review velocity).

·      F7. Author dashboard implementing all of the above. Should look intentional, not a Bootstrap CRUD template. Catalog view, per-book deep-dive, cross-book view, semantic search. (Plain Tailwind + shadcn is fine; we care about IA and clarity, not custom illustrations.)

·      F8. “Since you last logged in” affordance that surfaces meaningful review activity since the user’s last visit. You decide what “meaningful” means. Justify it.

·      F9. Scheduled re-ingest (cron / Celery beat / GitHub Actions / Vercel cron / Render cron, your choice). Document the trade-off.

·      F10. Weekly digest preview that renders the email the system would send. Real send not required, but the rendered output must be useful, not generic.

·      F11. Idempotent ingestion: running the same job twice produces the same final state, no duplicate reviews, no duplicate LLM calls for already-processed reviews.

·      F12. Multi-tenant isolation: author A cannot see author B’s books, reviews, or search results. Demonstrate the boundary in schema, queries, and API.

Non-functional

·      N1. Warm-start performance. Once the system is warm (not after a free-tier hibernation), a user (Daisy, an author) goes from “I have an ISBN” to “I see my dashboard with results” in under 60 seconds. We are not penalizing free-tier cold boots; we are checking that the ingest + analyze pipeline isn’t the bottleneck. Document any infra cold-start time you saw separately.

·      N2. The LLM call layer must be provider-agnostic enough to swap models (we use multi-provider: Anthropic + Gemini + OpenAI). One adapter layer, two implementations minimum.

·      N3. Cost-aware LLM usage. Track tokens + cost per analysis. Surface total spend per book + per author in the dashboard. The actual cost numbers matter for a startup.

·      N4. Structured logs. When something fails in the pipeline, you (or we) can answer “which review, what step, what error” from logs alone. No print statements.

·      N5. Rate-limit-aware LLM client with retries + exponential backoff. Show the policy. Document failure mode.

·      N6. Tests. Unit tests on the analysis layer (mock LLM); integration test on ingest, analyze, store happy path; one test demonstrating multi-tenant isolation can’t be bypassed. Aim for tests you’d actually want maintained, not 100% coverage theater.

·      N7. Documentation. README that gets a fresh engineer running locally in under 10 minutes. One short docs/ARCHITECTURE.md (one page max) explaining your major design decisions.

·      N8. Deployment. App reachable on a public URL. Free-tier deploy is fine (Vercel + Render + Supabase / Fly.io / Railway free tiers all work).

·      N9. Git hygiene. Small commits with sensible messages. We’ll skim your commit history.

·      N10. Webhook endpoint that fires on ingestion completion. Sign payloads with HMAC, document the signature scheme. Include a verification example in the docs.

·      N11. Auth: one author = one account, with session handling. Use any auth provider’s free tier (Supabase Auth, Clerk free, Auth0 free).

·      N12. One observability dashboard panel of your choice. Could be a /metrics endpoint, a Grafana board screenshot, a Sentry/Logflare/Axiom dashboard, or a simple admin page. Show how you’d debug the system at 3 AM.

The product-instinct requirement

·      P1. Build one thing not in this spec that you believe an author actually needs from a review-intelligence tool. Could be a feature, a workflow, an integration, a CLI command, a one-shot script. Anything. In your walkthrough, justify why you noticed this gap and what made you choose this specific addition.


This spec is larger than 8 hours of work, including with AI tools. That is intentional. We do not expect you to finish it. We expect you to read the whole thing, decide what matters, and ship what matters. If you ship at 8 hours with sharp cuts, great. If you ship at 20 hours because you wanted it, also great. Just tell us how long it actually took.


Stack notes

You can use whatever you want. To set expectations: Tweeds is Python + FastAPI + SQLAlchemy 2.0 + Postgres (pgvector) + Celery on the backend, and React + TypeScript + Vite + Tailwind + shadcn/ui (Radix-based) on the frontend. If you use this stack, your work translates directly to your first day with us. If you use something else (Next.js fullstack / Django / Go), that’s fine, but in your ARCHITECTURE.md briefly justify why you picked it.

What we don’t want: - LangChain “agent” wrappers around what should be a straight LLM call with Pydantic output. Use the SDKs directly (Anthropic / OpenAI / Gemini / Groq Python SDKs). - Pinecone / Weaviate / Chroma. Please use pgvector (it’s a Postgres extension; Supabase enables it with one click). You’ll work with pgvector at Tweeds. - Big frontend frameworks (Material UI / Chakra / Ant Design). Tailwind + shadcn/ui ships faster and looks better. - Boilerplate generators that produce 200 files of scaffolding. We’ll notice.


What we’ll evaluate

We grade what you shipped and how you reason about it, equally. The code shows what you can build under constraint; the walkthrough shows whether you can defend the choices. Strong submissions advance to a follow-up call where we go deeper.

We are not grading on: - Whether you finished every requirement. We expect you didn’t. - Lines of code, file count, test coverage percentage. - README polish. A 5-bullet “what works / what doesn’t / what I’d do next” is fine. - Production polish on the parts you intentionally deprioritized.


How to submit

Within 72 hours of receiving this email, reply with:

1.        Public GitHub repo URL.

2.        Deployed URL. Frontend that works without any setup on our side.

3.        Hours spent. One number, honest. We won’t penalize either direction.

4.        A short Loom or written walkthrough (max 5 minutes / 500 words) covering:

o   What you cut and why. Or, if you went over time, what you chose to overdeliver on and why that mattered.

o   The one decision you’d reverse now. Something you’d do differently if you started over today.

o   What’s interesting about the problem that wasn’t in the spec. What did you notice about “review intelligence for authors” that the assignment didn’t capture?

o   How AI tools shaped the work. Where they helped, where you overrode them, what they got wrong.

If your submission clears our review, you’ll receive a calendar invite for a 45-minute follow-up call to walk through it together.


Notes

·      If something is going to take >2 hours and you’re stuck, make a defensible call and write it down in your ARCHITECTURE.md as “I chose X because Y; with more time I’d reconsider Z.” We respect that more than fake completeness.

·      Use AI tools freely (Claude Code, Cursor, Copilot, ChatGPT, Codex). We expect you to. But you’ll be asked to defend every decision, so understand what your tools produced before you ship it.


Questions?

Reply to this email. We aim to respond within a working day. If a clarifying question would unblock you within an hour, just make a reasonable assumption and document it in the README. We care more about how you handle ambiguity than about us pre-answering everything.

Good luck!

Stefan & Daniel

•••
Go to
Page