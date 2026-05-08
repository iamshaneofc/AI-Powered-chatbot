import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.vectorstore.faiss_store import FAISSStore

def test_faiss_load_no_file(tmp_path):
    """Test loading gracefully ignores missing index files without crashing."""
    store = FAISSStore()
    with patch("app.vectorstore.faiss_store._INDEX_FILE", tmp_path / "missing.index"):
        store.load()
        assert store._index is None

def test_faiss_save_no_index():
    """Test saving an uninitialized index aborts safely."""
    store = FAISSStore()
    # should safely return without doing anything
    store.save()

def test_faiss_search_empty():
    """Test semantic search against an empty/uninitialized FAISS index."""
    store = FAISSStore()
    results = store.search([0.1, 0.2])
    assert results == []

def test_faiss_get_document_text_empty():
    """Test document text reconstruction on an empty docstore."""
    store = FAISSStore()
    assert store.get_document_text("test.pdf") == []

def test_faiss_get_document_text_match():
    """Test document reconstruction sorts chunks by chunk_index."""
    store = FAISSStore()
    store._metadatas = [{"source": "test.pdf", "chunk_index": 1}, {"source": "test.pdf", "chunk_index": 0}]
    store._texts = ["chunk 2", "chunk 1"]
    # We fake the lock for testing
    store._lock = MagicMock()
    store._lock.__enter__ = MagicMock()
    store._lock.__exit__ = MagicMock()
    
    texts = store.get_document_text("test.pdf")
    # Should be sorted chronologically
    assert texts == ["chunk 1", "chunk 2"]

def test_faiss_add_empty_vectors():
    """Test vector insertion gracefully ignores empty inputs."""
    store = FAISSStore()
    store.add([], [], [])
    assert store._index is None

def test_faiss_load_success(tmp_path):
    """Test loading an existing index and reading its docstore."""
    store = FAISSStore()
    
    mock_index = MagicMock()
    mock_index.ntotal = 10
    mock_index.d = 128
    
    index_file = tmp_path / "test.index"
    index_file.touch()
    
    docstore_file = tmp_path / "test.json"
    docstore_file.write_text('{"texts": ["a"], "metadatas": [{}]}')
    
    with patch("faiss.read_index", return_value=mock_index), \
         patch("app.vectorstore.faiss_store._INDEX_FILE", index_file), \
         patch("app.vectorstore.faiss_store._DOCSTORE_FILE", docstore_file):
        
        store.load()
        assert store.total_vectors == 10
        assert store._texts == ["a"]

def test_faiss_properties():
    """Test LangChain compatibility properties."""
    store = FAISSStore()
    store._texts = ["test"]
    assert store.docstore == ["test"]
    assert store.index_to_docstore_id == {0: 0}
