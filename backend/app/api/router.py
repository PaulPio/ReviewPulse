"""
Main API router.

Route organisation
------------------
/auth/*      — register, login, me
/books/*     — catalog CRUD + stats
/books/{id}/reviews   — per-book review list (in reviews router)
/books/{id}/ingest    — trigger ingestion job (in jobs router)
/books/{id}/trends    — sentiment/theme timeline (in analytics router)
/jobs/*      — job status polling
/search      — semantic search across catalog
/compare     — cross-book comparison
/whats-new   — activity since last login
/digest      — weekly digest preview
/audience-insights — P1: reader segment clustering
/webhooks/*  — webhook delivery history
/metrics     — observability panel (N12)
"""

from fastapi import APIRouter

from app.api.authors import router as authors_router
from app.api.books import router as books_router
from app.api.reviews import router as reviews_router
from app.api.search import router as search_router
from app.api.analytics import router as analytics_router
from app.api.jobs import router as jobs_router
from app.api.webhooks import router as webhooks_router
from app.api.metrics import router as metrics_router

api_router = APIRouter()

api_router.include_router(authors_router, prefix="/auth", tags=["Auth"])
api_router.include_router(books_router, prefix="/books", tags=["Books"])
api_router.include_router(reviews_router, tags=["Reviews"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(analytics_router, tags=["Analytics"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])
