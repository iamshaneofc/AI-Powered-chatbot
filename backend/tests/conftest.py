import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    """
    Route the FAISS index and the uploads directory into a per-test temp dir.

    Keeps tests hermetic (no leftover index from a previous run) and stops the
    suite from writing into the real backend/data folder.
    """
    from app.vectorstore import faiss_store as faiss_module
    from app.config import settings

    vector_dir = tmp_path / "vectorstore"
    vector_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(faiss_module, "_INDEX_FILE", vector_dir / "index.index")
    monkeypatch.setattr(faiss_module, "_DOCSTORE_FILE", vector_dir / "index.json")

    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", uploads)

    # Drop in-memory state left over from a previous test
    store = faiss_module.faiss_store
    store._index = None
    store._texts = []
    store._metadatas = []
    store._dim = None
    store._loaded_mtime = None


@pytest.fixture
def client(isolate_storage):
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_openai():
    with patch("app.services.openai_service.OpenAIService.chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.services.openai_service.OpenAIService.embed_batch", new_callable=AsyncMock) as mock_embed, \
         patch("app.services.openai_service.OpenAIService.embed", new_callable=AsyncMock) as mock_single_embed:
        mock_chat.return_value = "Mocked LLM answer"
        mock_embed.return_value = [[0.1] * 1536] # 1536-dim dummy embedding
        mock_single_embed.return_value = [0.1] * 1536
        yield mock_chat, mock_embed

@pytest.fixture
def mock_whisper():
    with patch("app.services.whisper_service.WhisperService.transcribe_with_meta", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = {
            "text": "Mocked transcript",
            "language": "en",
            "duration": 5.0,
            "segments": [{"start": 0.0, "end": 5.0, "text": "Mocked transcript"}]
        }
        yield mock_transcribe

@pytest.fixture
def mock_pdf_extract():
    with patch("app.routes.upload.extract_text") as mock_extract:
        mock_extract.return_value = "This is a mocked PDF text."
        yield mock_extract
@pytest.fixture(autouse=True)
def mock_redis():
    with patch("app.services.redis_service.RedisService.client", new_callable=MagicMock), \
         patch("app.services.redis_service.redis_service.add_history", new_callable=AsyncMock) as mock_add, \
         patch("app.services.redis_service.redis_service.get_history", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        yield mock_add, mock_get
