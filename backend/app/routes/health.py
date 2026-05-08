"""routes/health.py — Health & readiness endpoints.

GET /api/v1/health        → liveness probe (always 200 if the process is up)
GET /api/v1/health/ready  → readiness probe (checks downstream dependencies)
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()

# Record process start time for uptime calculation
_START_TIME = time.time()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    uptime_seconds: float
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict


# ---------------------------------------------------------------------------
# Liveness — is the process alive?
# ---------------------------------------------------------------------------
@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health_check():
    """Returns 200 as long as the server process is running."""
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=round(time.time() - _START_TIME, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Readiness — are all dependencies available?
# ---------------------------------------------------------------------------
@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness check")
async def readiness_check():
    """
    Checks key integrations and returns their status.
    Returns HTTP 503 if any critical dependency is unavailable.
    """
    from fastapi import Response
    from fastapi.responses import JSONResponse

    checks: dict[str, str] = {}

    # ── FAISS vector store ────────────────────────────────────────────────
    try:
        from app.vectorstore.faiss_store import faiss_store
        checks["faiss"] = "ok" if faiss_store.is_ready() else "not_initialised"
    except Exception as e:
        checks["faiss"] = f"error: {e}"

    # ── Upload directory ──────────────────────────────────────────────────
    checks["upload_dir"] = "ok" if settings.UPLOAD_DIR.exists() else "missing"

    # ── OpenAI API key present (not validated, just presence check) ───────
    checks["openai_key"] = "configured" if settings.OPENAI_API_KEY else "missing"

    overall = "ok" if all(v in ("ok", "configured", "not_initialised") for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content=ReadinessResponse(status=overall, checks=checks).model_dump(),
    )
