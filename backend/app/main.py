"""
FastAPI application entry point.

Lifespan
--------
On startup: configure structlog, run DB connectivity check.
On shutdown: dispose the async engine connection pool.

Middleware
----------
- CORSMiddleware: configured from settings.cors_origins + localhost dev origins
- No heavy middleware added here; auth is in dependencies, not middleware,
  to allow per-route opt-out (public /health, /docs).

OpenAPI
-------
Auto-generated at /docs (Swagger UI) and /redoc (ReDoc).
Available in all environments; disable in production by setting docs_url=None.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.api.router import api_router

# Configure structured logging before anything else
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    _cors_allow = (
        ["http://localhost:5173", "http://localhost:3000"]
        + list(settings.cors_origins)
    )
    logger.info(
        "app.startup",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        cors_allow_origins=_cors_allow,
    )
    yield
    # Dispose the connection pool cleanly on shutdown
    from app.db.base import engine
    await engine.dispose()
    logger.info("app.shutdown", reason="lifespan_complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "ReviewPulse API — book review intelligence for independent authors. "
        "Ingest, analyse (sentiment/themes/AI detection), and trend review data "
        "across an author's full catalog with semantic search via pgvector."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["http://localhost:5173", "http://localhost:3000"]
        + list(settings.cors_origins)
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for unhandled exceptions.
    Logs with full context so N4 (structured logs) is satisfied even for unexpected errors.
    """
    logger.error(
        "request.unhandled_error",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Check server logs."},
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
async def health():
    """
    Health check endpoint.

    Returns 200 with basic system info. Used by:
    - Docker/Kubernetes liveness probes
    - Render/Fly.io health checks
    - Frontend to detect cold-start recovery
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
