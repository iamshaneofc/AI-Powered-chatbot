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


# ---------------------------------------------------------------------------
# Cross-process (multi-worker) consistency
# ---------------------------------------------------------------------------
def _index_kb(path, texts, metadatas, vector=(1.0, 0.0, 0.0, 0.0)):
    """Create a small FAISS index on disk, as if another worker had saved it."""
    writer = FAISSStore()
    with patch("app.vectorstore.faiss_store._INDEX_FILE", path / "kb.index"), \
         patch("app.vectorstore.faiss_store._DOCSTORE_FILE", path / "kb.json"):
        writer.add(vectors=[list(vector)], texts=texts, metadatas=metadatas)
        writer.save()
    return writer


def test_search_reloads_index_written_by_another_worker(tmp_path):
    """A worker that started with an empty index must pick up another worker's save."""
    _index_kb(tmp_path, ["hello world"], [{"source": "a.pdf"}])

    with patch("app.vectorstore.faiss_store._INDEX_FILE", tmp_path / "kb.index"), \
         patch("app.vectorstore.faiss_store._DOCSTORE_FILE", tmp_path / "kb.json"):
        reader = FAISSStore()
        assert reader._index is None          # no in-memory snapshot yet

        results = reader.search([1.0, 0.0, 0.0, 0.0])
        assert len(results) == 1
        assert results[0]["metadata"]["source"] == "a.pdf"
        assert reader.is_ready()
        assert reader.sources == ["a.pdf"]
        assert reader.total_vectors == 1


def test_search_sees_index_cleared_by_another_worker(tmp_path):
    """A clear() in one worker must not leave ghost chunks in another."""
    writer = _index_kb(tmp_path, ["hello world"], [{"source": "a.pdf"}])

    with patch("app.vectorstore.faiss_store._INDEX_FILE", tmp_path / "kb.index"), \
         patch("app.vectorstore.faiss_store._DOCSTORE_FILE", tmp_path / "kb.json"):
        reader = FAISSStore()
        assert reader.search([1.0, 0.0, 0.0, 0.0])
        assert reader.is_ready()

        writer.clear()                        # another worker resets the KB

        assert reader.is_ready() is False
        assert reader.search([1.0, 0.0, 0.0, 0.0]) == []
        assert reader.sources == []


def test_load_missing_file_resets_stale_state(tmp_path):
    """Loading after the index file vanished must drop stale in-memory data."""
    store = FAISSStore()
    store._index = MagicMock()
    store._index.ntotal = 5
    store._texts = ["stale"]

    with patch("app.vectorstore.faiss_store._INDEX_FILE", tmp_path / "gone.index"):
        store.load()
        assert store._index is None
        assert store.total_vectors == 0


def test_save_is_visible_to_second_store(tmp_path):
    """save() then a fresh store.load() must reproduce the docstore."""
    with patch("app.vectorstore.faiss_store._INDEX_FILE", tmp_path / "kb.index"), \
         patch("app.vectorstore.faiss_store._DOCSTORE_FILE", tmp_path / "kb.json"):
        writer = FAISSStore()
        writer.add(vectors=[[1.0, 0.0, 0.0, 0.0]], texts=["chunk a"], metadatas=[{"source": "doc.pdf", "chunk_index": 0}])
        writer.save()

        reader = FAISSStore()
        reader.load()
        assert reader.total_vectors == 1
        assert reader.get_document_text("doc.pdf") == ["chunk a"]
