"""routes/transcribe.py — Whisper transcription endpoints.

POST /api/v1/transcribe          → transcribe an already-uploaded file by filename
POST /api/v1/transcribe/upload   → upload + transcribe in one shot (no indexing)
"""

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.utils.file_utils import save_upload, validate_file
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

MEDIA_EXTS = {"mp3", "mp4", "wav", "m4a", "webm"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class TranscribeRequest(BaseModel):
    filename: str


class TranscribeResponse(BaseModel):
    filename: str
    transcript: str
    language: str | None = None
    duration_seconds: float | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/transcribe", response_model=TranscribeResponse, summary="Transcribe saved file")
async def transcribe_saved(req: TranscribeRequest):
    """
    Transcribe a file that was previously uploaded via /upload/media.
    The filename must match a file in the uploads directory.
    """
    target = settings.UPLOAD_DIR / req.filename
    if not target.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File '{req.filename}' not found in upload directory.",
        )

    ext = target.suffix.lstrip(".").lower()
    if ext not in MEDIA_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"File must be an audio/video type ({MEDIA_EXTS}).",
        )

    try:
        from app.services.whisper_service import whisper_service
        result = await whisper_service.transcribe_with_meta(target)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Transcription failed for %s: %s", req.filename, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TranscribeResponse(
        filename=req.filename,
        transcript=result["text"],
        language=result.get("language"),
        duration_seconds=result.get("duration"),
    )


@router.post(
    "/transcribe/upload",
    response_model=TranscribeResponse,
    summary="Upload & transcribe in one shot",
)
async def upload_and_transcribe(file: UploadFile = File(...)):
    """
    Convenience endpoint — saves the file then immediately returns
    the transcript. Does NOT index the transcript into FAISS.
    """
    ext = Path(file.filename).suffix.lstrip(".").lower()
    if ext not in MEDIA_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Expected audio/video ({MEDIA_EXTS}), got '{file.filename}'.",
        )

    validate_file(file)
    saved_path = await save_upload(file)

    try:
        from app.services.whisper_service import whisper_service
        result = await whisper_service.transcribe_with_meta(saved_path)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TranscribeResponse(
        filename=saved_path.name,
        transcript=result["text"],
        language=result.get("language"),
        duration_seconds=result.get("duration"),
    )
