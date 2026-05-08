"""routes/query.py — RAG-powered Q&A endpoints.

POST /api/v1/query          → ask a question against the indexed knowledge base
POST /api/v1/query/direct   → ask GPT directly without context (no RAG)
GET  /api/v1/query/history  → retrieve recent Q&A pairs (in-memory, demo only)
"""

from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, examples=["What is the main topic of the document?"])
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")
    session_id: str = Field(default="default_session", description="Unique ID for chat history persistence")
    filename: str | None = Field(default=None, description="Optional: filter search to a specific file")

class RetrievedChunk(BaseModel):
    text: str
    score: float
    source: str
    timestamp: str | None = None

class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[RetrievedChunk]
    model: str
    timestamp: str

class DirectQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        max_length=500,
    )

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse, summary="RAG-powered Chat Q&A")
async def chat_endpoint(req: ChatRequest):
    """
    Full RAG pipeline:
      1. Retrieve top-k relevant chunks (optionally filtered by filename)
      2. Build RAG context from retrieved chunks
      3. Generate answer using OpenAI API
      4. Persist Q&A to Redis history
    """
    try:
        from app.services.rag_service import rag_service
        from app.services.redis_service import redis_service
        
        # Run RAG pipeline
        result = await rag_service.answer(
            question=req.question, 
            top_k=req.top_k,
            filename_filter=req.filename
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Format the retrieved chunks for the response
    formatted_sources = []
    for chunk in result.get("chunks", []):
        meta = chunk.get("metadata", {})
        
        timestamp_val = None
        if "start" in meta:
            timestamp_val = str(meta["start"])
        elif "timestamp" in meta:
            timestamp_val = str(meta["timestamp"])
            
        formatted_sources.append(RetrievedChunk(
            text=chunk.get("text", ""),
            score=chunk.get("score", 0.0),
            source=meta.get("source", "unknown"),
            timestamp=timestamp_val
        ))

    record = {
        "question": req.question,
        "answer": result["answer"],
        "sources": [s.source for s in formatted_sources],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": req.session_id
    }
    
    # Persist to Redis
    await redis_service.add_history(req.session_id, record)

    return ChatResponse(
        question=req.question,
        answer=result["answer"],
        sources=formatted_sources,
        model=result.get("model", "unknown"),
        timestamp=record["timestamp"],
    )


@router.post("/query/direct", summary="Direct GPT query (no RAG)")
async def direct_query(req: DirectQueryRequest):
    """Send a question directly to GPT without retrieving document context."""
    try:
        from app.services.openai_service import openai_service
        answer = await openai_service.chat(
            user_message=req.question,
            system_prompt=req.system_prompt,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"question": req.question, "answer": answer}


@router.get("/query/history", summary="Recent Q&A history")
async def get_history(session_id: str = "default_session", limit: int = 10):
    """Return the most recent Q&A pairs from Redis."""
    from app.services.redis_service import redis_service
    history = await redis_service.get_history(session_id, limit=limit)
    return {"total": len(history), "session_id": session_id, "history": history}
