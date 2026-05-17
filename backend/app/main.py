from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_routes import router as auth_router
from app.api.books_routes import router as books_router
from app.api.discovery_routes import router as discovery_router
from app.api.inbound_webhook_routes import router as inbound_webhook_router
from app.api.jobs_routes import router as jobs_router
from app.api.metrics_routes import router as metrics_router
from app.config import get_settings
from app.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="ReviewPulse API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(inbound_webhook_router, prefix="/api/v1")
app.include_router(books_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(discovery_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "reviewpulse", "docs": "/docs"}
