"""routes/upload.py — Document & media upload endpoints.

POST /api/v1/upload/document  → upload PDF / DOCX / TXT, chunk & index into FAISS
POST /api/v1/upload/media     → upload audio/video for Whisper transcription
GET  /api/v1/upload/files     → list all uploaded files
DELETE /api/v1/upload/files/{filename} → remove a file
"""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.utils.file_utils import extract_text, save_upload, validate_file
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

DOCUMENT_EXTS = {"pdf", "txt", "docx"}
MEDIA_EXTS    = {"mp3", "mp4", "wav", "m4a", "webm"}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    filename: str
    saved_as: str
    size_kb: float
    message: str


class FileListResponse(BaseModel):
    total: int
    files: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ext(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()

async def _reset_state_before_upload(session_id: str = "default_session"):
    """Clear FAISS, previous uploads, and chat history before a new upload."""
    from app.vectorstore.faiss_store import faiss_store
    from app.services.redis_service import redis_service
    import shutil
    
    faiss_store.clear()
    
    upload_path = Path(settings.UPLOAD_DIR)
    if upload_path.exists():
        for item in upload_path.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                logger.warning("Could not delete old file %s: %s", item, e)
                
    await redis_service.clear_history(session_id)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class PDFUploadResponse(BaseModel):
    filename: str
    message: str
    chunks: int
    metadata: dict


@router.post("/upload/pdf", response_model=PDFUploadResponse, summary="Upload and process a PDF synchronously")
async def upload_pdf(
    file: UploadFile = File(...),
):
    """
    Accept a PDF file, extract text, chunk it, generate embeddings,
    and store them in FAISS, all synchronously in the request flow.
    """
    if _ext(file.filename) != "pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Expected a PDF file, got '{file.filename}'.",
        )

    try:
        # 0. Reset state so AI only focuses on the new file
        await _reset_state_before_upload()

        # 1. Save uploaded PDF in uploads/
        validate_file(file)
        saved_path = await save_upload(file)

        # 2. Extract text using PDF service
        from app.services.pdf_service import pdf_service
        text = pdf_service.extract_text(saved_path)

        if not text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")

        # 3. Implement text chunking utility
        from app.utils.text_chunker import chunk_text
        chunks = chunk_text(text, chunk_size=settings.VECTOR_CHUNK_SIZE, overlap=settings.VECTOR_CHUNK_OVERLAP)

        # 4. Generate embeddings using OpenAI service
        from app.services.openai_service import openai_service
        vectors = await openai_service.embed_batch(chunks)

        # 5. Store embeddings in FAISS
        from app.vectorstore.faiss_store import faiss_store
        
        # Build metadata for each chunk
        doc_metadata = {"source": file.filename, "size_kb": round(saved_path.stat().st_size / 1024, 2)}
        metadatas = [
            {**doc_metadata, "chunk_index": i, "chunk_total": len(chunks)}
            for i in range(len(chunks))
        ]
        
        faiss_store.add(vectors=vectors, texts=chunks, metadatas=metadatas)
        faiss_store.save()

        # 6. Return response
        return PDFUploadResponse(
            filename=file.filename,
            message="PDF uploaded and processed successfully.",
            chunks=len(chunks),
            metadata=doc_metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process PDF %s: %s", file.filename, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@router.post("/upload/document", response_model=UploadResponse, summary="Upload a document")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Accept PDF, DOCX, or TXT files.
    After saving, kicks off a background task to extract text,
    chunk it, embed it, and add to the FAISS index.
    """
    if _ext(file.filename) not in DOCUMENT_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Expected a document file ({DOCUMENT_EXTS}), got '{file.filename}'.",
        )

    # 0. Reset state so AI only focuses on the new file
    await _reset_state_before_upload()

    validate_file(file)
    saved_path = await save_upload(file)

    background_tasks.add_task(_index_document, saved_path)

    return UploadResponse(
        filename=file.filename,
        saved_as=saved_path.name,
        size_kb=round(saved_path.stat().st_size / 1024, 2),
        message="Document saved. Indexing started in background.",
    )


class MediaUploadResponse(BaseModel):
    filename: str
    message: str
    transcript_length: int
    chunks: int
    timestamps: list[dict]

@router.post("/upload/media", response_model=MediaUploadResponse, summary="Upload and process media synchronously")
async def upload_media(
    file: UploadFile = File(...),
):
    """
    Accept audio/video files (mp3, mp4, wav, m4a, webm).
    Synchronously extracts transcription with timestamps,
    chunks it, embeds it, and stores in FAISS.
    """
    if _ext(file.filename) not in MEDIA_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Expected a media file ({MEDIA_EXTS}), got '{file.filename}'.",
        )

    try:
        # 0. Reset state so AI only focuses on the new file
        await _reset_state_before_upload()

        validate_file(file)
        saved_path = await save_upload(file)

        from app.services.whisper_service import whisper_service
        from app.utils.text_chunker import chunk_transcript
        from app.services.openai_service import openai_service
        from app.vectorstore.faiss_store import faiss_store

        # 1. Transcribe with timestamps
        meta = await whisper_service.transcribe_with_meta(saved_path)
        transcript = meta.get("text", "")
        if not transcript.strip():
             raise HTTPException(status_code=400, detail="Empty transcript returned.")
             
        # 2. Chunk transcript preserving timestamps
        chunks_data = chunk_transcript(meta.get("segments", []), chunk_size=settings.VECTOR_CHUNK_SIZE)
        texts = [c["text"] for c in chunks_data]

        # 3. Generate embeddings
        vectors = await openai_service.embed_batch(texts)

        # 4. Store in FAISS with metadata
        doc_metadata = {"source": file.filename, "size_kb": round(saved_path.stat().st_size / 1024, 2), "type": "transcript"}
        metadatas = [
            {
                **doc_metadata,
                "chunk_index": i,
                "chunk_total": len(texts),
                "start": c["start"],
                "end": c["end"]
            }
            for i, c in enumerate(chunks_data)
        ]
        
        faiss_store.add(vectors=vectors, texts=texts, metadatas=metadatas)
        faiss_store.save()

        # Build timestamps for response
        timestamps = [{"start": c["start"], "end": c["end"]} for c in chunks_data]

        return MediaUploadResponse(
            filename=file.filename,
            message="Media uploaded and transcribed successfully.",
            transcript_length=len(transcript),
            chunks=len(texts),
            timestamps=timestamps
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process media %s: %s", file.filename, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process media: {str(e)}")


@router.get("/upload/files", response_model=FileListResponse, summary="List uploaded files")
async def list_files():
    """Returns all files currently in the upload directory."""
    files = [f.name for f in settings.UPLOAD_DIR.iterdir() if f.is_file()]
    return FileListResponse(total=len(files), files=sorted(files))


@router.delete("/upload/files/{filename}", summary="Delete an uploaded file")
async def delete_file(filename: str):
    """Permanently delete a file from the upload directory."""
    target = settings.UPLOAD_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    target.unlink()
    logger.info("Deleted file: %s", filename)
    return {"message": f"'{filename}' deleted successfully."}


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------
async def _index_document(path: Path) -> None:
    """Extract text → chunk → embed → add to FAISS."""
    try:
        from app.services.vector_service import vector_service
        text = extract_text(path)
        if text.strip():
            await vector_service.add_text(text, metadata={"source": path.name})
            logger.info("Indexed document: %s", path.name)
        else:
            logger.warning("No text extracted from %s", path.name)
    except Exception as exc:
        logger.error("Failed to index %s: %s", path.name, exc, exc_info=True)


async def _transcribe_and_index(path: Path) -> None:
    """Whisper transcription → embed → add to FAISS."""
    try:
        from app.services.whisper_service import whisper_service
        from app.services.vector_service import vector_service

        transcript = await whisper_service.transcribe(path)
        if transcript.strip():
            await vector_service.add_text(transcript, metadata={"source": path.name, "type": "transcript"})
            logger.info("Transcribed and indexed: %s", path.name)
        else:
            logger.warning("Empty transcript for %s", path.name)
    except Exception as exc:
        logger.error("Failed to transcribe/index %s: %s", path.name, exc, exc_info=True)
