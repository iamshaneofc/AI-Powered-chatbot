from fastapi import APIRouter, HTTPException
import shutil
from pathlib import Path
from app.config import settings
from app.vectorstore.faiss_store import faiss_store
from app.services.redis_service import redis_service
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.delete("/reset", summary="Reset entire application state")
async def reset_state(session_id: str = "default_session"):
    """
    Clears everything:
    1. Resets FAISS vector index
    2. Deletes all files in the upload directory
    3. Wipes Redis chat history for the session
    """
    try:
        # 1. Clear FAISS
        faiss_store.clear()
        
        # 2. Clear Uploads
        upload_path = Path(settings.UPLOAD_DIR)
        if upload_path.exists():
            for item in upload_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        logger.info("Upload directory cleared")

        # 3. Clear Redis History
        await redis_service.clear_history(session_id)
        logger.info(f"Chat history cleared for session: {session_id}")

        return {"status": "success", "message": "Application state reset successfully"}
    
    except Exception as e:
        logger.error(f"Error during reset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
