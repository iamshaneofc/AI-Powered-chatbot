import pytest
from unittest.mock import AsyncMock, patch

from app.services.rag_service import rag_service

@pytest.mark.asyncio
async def test_rag_service_hallucination_fallback():
    """Test that the RAG service returns a fallback message when no chunks are retrieved."""
    with patch("app.services.vector_service.VectorService.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        
        result = await rag_service.answer("What is the secret code?")
        
        assert "No relevant documents found" in result["answer"]
        assert result["sources"] == []
        assert result["chunks"] == []

@pytest.mark.asyncio
async def test_rag_service_retrieval_flow(mock_openai):
    """Test the full retrieval flow, including metadata propagation and LLM call."""
    with patch("app.services.vector_service.VectorService.search", new_callable=AsyncMock) as mock_search:
        # Mock vector service returning 2 relevant chunks from different sources
        mock_search.return_value = [
            {"text": "Chunk 1 about AI.", "score": 0.9, "metadata": {"source": "doc1.pdf"}},
            {"text": "Chunk 2 about AI.", "score": 0.8, "metadata": {"source": "doc2.pdf"}}
        ]
        
        # Use the mock_openai fixture to simulate LLM response
        result = await rag_service.answer("What is AI?", session_id="test_session")
        
        assert result["answer"] == "Mocked LLM answer"
        assert result["sources"] == ["doc1.pdf", "doc2.pdf"]
        assert len(result["chunks"]) == 2
        
        # Verify the chunks are passed through correctly
        assert result["chunks"][0]["metadata"]["source"] == "doc1.pdf"
