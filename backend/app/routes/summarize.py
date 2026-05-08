from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.logger import get_logger
from app.services.summarization_service import summarization_service

router = APIRouter()
logger = get_logger(__name__)

class SummarizeRequest(BaseModel):
    filename: str = Field(..., description="The name of the file to summarize.")
    summary_type: str = Field(default="detailed", description="Type of summary: 'brief', 'detailed', or 'bullet points'.")

class SummarizeResponse(BaseModel):
    filename: str
    summary_type: str
    summary: str

@router.post("/summarize", response_model=SummarizeResponse, summary="Generate a document summary")
async def summarize_document(req: SummarizeRequest):
    """
    Retrieve document text from FAISS and generate a summary using OpenAI.
    """
    try:
        summary_text = await summarization_service.summarize(
            filename=req.filename,
            summary_type=req.summary_type
        )
        return SummarizeResponse(
            filename=req.filename,
            summary_type=req.summary_type,
            summary=summary_text
        )
    except ValueError as e:
        logger.error("Summarization error: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to summarize %s: %s", req.filename, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")
