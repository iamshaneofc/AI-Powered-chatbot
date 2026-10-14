import pytest
from unittest.mock import AsyncMock, patch

from app.services.rag_service import rag_service

@pytest.mark.asyncio
async def test_rag_service_empty_index_fallback():
    """No chunks + empty index → tell the user nothing is uploaded yet."""
    with patch("app.services.vector_service.VectorService.search", new_callable=AsyncMock) as mock_search, \
         patch.object(rag_service, "_knowledge_state", return_value=(False, [])):
        mock_search.return_value = []

        result = await rag_service.answer("What is the secret code?")

        assert "don't have any documents indexed yet" in result["answer"]
        assert result["sources"] == []
        assert result["chunks"] == []

@pytest.mark.asyncio
async def test_rag_service_index_ready_but_no_match():
    """No chunks while an index exists → mention the indexed files."""
    with patch("app.services.vector_service.VectorService.search", new_callable=AsyncMock) as mock_search, \
         patch.object(rag_service, "_knowledge_state", return_value=(True, ["Snehanshu_Resume_AI_Engineer.pdf"])):
        mock_search.return_value = []

        result = await rag_service.answer("quantum banana recipe")

        assert "couldn't find anything relevant" in result["answer"]
        assert "Snehanshu_Resume_AI_Engineer.pdf" in result["answer"]
        assert result["chunks"] == []

@pytest.mark.asyncio
async def test_rag_service_greeting_aware_of_index():
    """Casual greeting acknowledges documents that are already indexed."""
    with patch.object(rag_service, "_knowledge_state", return_value=(True, ["resume.pdf"])):
        result = await rag_service.answer("hi")

        assert "resume.pdf" in result["answer"]
        assert result["chunks"] == []

@pytest.mark.asyncio
async def test_rag_service_greeting_without_index():
    """Greeting falls back to the generic onboarding message when empty."""
    with patch.object(rag_service, "_knowledge_state", return_value=(False, [])):
        result = await rag_service.answer("hello")

        assert "upload a file to get started" in result["answer"]
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

@pytest.mark.asyncio
async def test_rag_service_uses_conversation_history(mock_openai):
    """History for the session must be injected into the prompt context."""
    fake_history = [
        {"question": "Who is Snehanshu?", "answer": "An AI engineer."},
    ]
    with patch("app.services.vector_service.VectorService.search", new_callable=AsyncMock) as mock_search, \
         patch("app.services.redis_service.redis_service.get_history", new_callable=AsyncMock) as mock_hist:
        mock_search.return_value = [{"text": "ctx", "score": 0.5, "metadata": {"source": "a.pdf"}}]
        mock_hist.return_value = fake_history

        await rag_service.answer("Tell me more", session_id="sess-1")

        mock_hist.assert_awaited_once_with("sess-1", limit=5)
        context = mock_openai[0].call_args.kwargs["context"]
        assert "Previous conversation:" in context
        assert "Who is Snehanshu?" in context
