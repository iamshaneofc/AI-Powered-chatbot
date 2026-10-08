"""
main.py — Application entry point.

Bootstraps the FastAPI app with:
  - CORS middleware (configured via .env)
  - All route modules registered under /api/v1
  - Startup / shutdown lifespan hooks
  - Global exception handler for clean JSON errors
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.routes import health, upload, query, transcribe, summarize, reset, settings as settings_route
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — runs once on startup and on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise heavy resources (vector store, model caches) on startup."""
    logger.info("🚀  Starting AI Q&A backend — environment: %s", settings.ENVIRONMENT)

    # Lazy-import so the app still boots even if FAISS index doesn't exist yet
    try:
        from app.vectorstore.faiss_store import faiss_store
        faiss_store.load()
        logger.info("✅  FAISS vector store loaded")
    except Exception as exc:
        logger.warning("⚠️  FAISS store not loaded (will be created on first upload): %s", exc)

    yield  # ← application runs here

    logger.info("🛑  Shutting down — releasing resources")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered document & multimedia Q&A API",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────
    # Fixed CORS configuration: allow all origins, which requires allow_credentials=False
    # This prevents OPTIONS 400 errors for cross-origin preflight requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Root redirect ─────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    # ── Routers ───────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(health.router,     prefix=prefix, tags=["Health"])
    app.include_router(upload.router,     prefix=prefix, tags=["Upload"])
    app.include_router(query.router,      prefix=prefix, tags=["Query"])
    app.include_router(transcribe.router, prefix=prefix, tags=["Transcribe"])
    app.include_router(summarize.router,  prefix=prefix, tags=["Summarize"])
    app.include_router(reset.router,      prefix=prefix, tags=["Reset"])
    app.include_router(settings_route.router, prefix=f"{prefix}/settings", tags=["Settings"])

    # ── Global exception handlers ─────────────────────────────────────────
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f"HTTP Error {exc.status_code} on {request.url.path}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "path": request.url.path,
                "status_code": exc.status_code
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation Error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "message": "Invalid request payload.",
                "details": exc.errors(),
                "path": request.url.path
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "An internal server error occurred.",
                "detail": str(exc),
                "path": request.url.path
            },
        )

    return app


app = create_app()
