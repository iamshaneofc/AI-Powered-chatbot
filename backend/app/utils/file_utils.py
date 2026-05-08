"""
utils/file_utils.py — File handling helpers.

Responsibilities:
  - Validate file extension and size
  - Save uploaded files to the upload directory with a UUID-based name
  - Extract raw text from supported document types (PDF, DOCX, TXT)
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Ensure upload directory exists at import time
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_file(file: UploadFile) -> None:
    """Raise HTTP 400 if the file extension or size is not allowed."""
    ext = _get_extension(file.filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{ext}' is not supported. "
                   f"Allowed: {settings.ALLOWED_EXTENSIONS}",
        )


def _get_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is missing.")
    return Path(filename).suffix.lstrip(".").lower()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

async def save_upload(file: UploadFile) -> Path:
    """
    Persist an UploadFile to disk.

    Returns the Path of the saved file.
    Raises HTTP 413 if the file exceeds MAX_UPLOAD_SIZE_MB.
    """
    ext = _get_extension(file.filename)
    dest = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total = 0

    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 64):   # 64 KB chunks
            total += len(chunk)
            if total > max_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                )
            f.write(chunk)

    logger.info("Saved upload → %s  (%.1f KB)", dest.name, total / 1024)
    return dest


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(file_path: Path) -> str:
    """
    Extract plain text from a document file.

    Supported: .pdf, .docx, .txt
    Returns empty string for unsupported types (caller decides what to do).
    """
    ext = file_path.suffix.lstrip(".").lower()

    if ext == "txt":
        return file_path.read_text(encoding="utf-8", errors="replace")

    if ext == "pdf":
        return _extract_pdf(file_path)

    if ext == "docx":
        return _extract_docx(file_path)

    logger.warning("Text extraction not supported for .%s", ext)
    return ""


def _extract_pdf(path: Path) -> str:
    try:
        import pypdf  # pypdf ≥ 3.x

        reader = pypdf.PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except ImportError:
        raise RuntimeError("pypdf is not installed. Add it to requirements.txt.")


def _extract_docx(path: Path) -> str:
    try:
        import docx  # python-docx

        doc = docx.Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        raise RuntimeError("python-docx is not installed. Add it to requirements.txt.")
