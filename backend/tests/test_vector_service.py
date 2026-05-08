import pytest
from unittest.mock import patch

from app.services.vector_service import vector_service

def test_chunk_text():
    """Test the chunking logic deterministically."""
    text = "A" * 100
    chunks = vector_service._chunk_text(text, chunk_size=40, overlap=10)
    
    assert len(chunks) == 4
    # 0 to 40 (length 40)
    # 30 to 70 (length 40)
    # 60 to 100 (length 40)
    # 90 to 100 (length 10)
    assert chunks[0] == "A" * 40
    assert chunks[1] == "A" * 40
    assert chunks[2] == "A" * 40
    assert chunks[3] == "A" * 10

@pytest.mark.asyncio
async def test_add_text():
    """Test inserting text, ensuring it gets chunked and sent to FAISS correctly."""
    with patch("app.vectorstore.faiss_store.faiss_store.add") as mock_faiss_add, \
         patch("app.vectorstore.faiss_store.faiss_store.save") as mock_faiss_save:
        
        num_chunks = await vector_service.add_text(
            text="This is a test document.",
            metadata={"source": "test.txt"},
            chunk_size=10,
            overlap=2
        )
        
        assert num_chunks > 0
        mock_faiss_add.assert_called_once()
        mock_faiss_save.assert_called_once()
        
        # Validate metadata propagation
        args, kwargs = mock_faiss_add.call_args
        metadatas = kwargs.get("metadatas") or args[2]
        assert metadatas[0]["source"] == "test.txt"
        assert "chunk_index" in metadatas[0]

@pytest.mark.asyncio
async def test_search():
    """Test semantic search hitting the FAISS store."""
    with patch("app.vectorstore.faiss_store.faiss_store.search") as mock_faiss_search:
        mock_faiss_search.return_value = [{"text": "Result 1", "score": 0.99, "metadata": {}}]
        
        results = await vector_service.search("semantic search query", top_k=2)
        
        assert len(results) == 1
        assert results[0]["text"] == "Result 1"
        mock_faiss_search.assert_called_once()
