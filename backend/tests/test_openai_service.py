import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from openai import APIError, RateLimitError, APIConnectionError
import httpx
from app.config import settings
from app.services.openai_service import OpenAIService

@pytest.fixture
def clean_openai(monkeypatch):
    """Fresh OpenAIService pinned to a known provider so mocks are reused."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", settings.OPENAI_API_KEY or "test-key")
    return OpenAIService()


def _install_client(svc: OpenAIService, mock_client) -> None:
    """
    Put a mock transport behind the service.

    Also mirrors the current provider/key so `_ensure_client()` does not
    replace our mock with a real AsyncOpenAI client.
    """
    svc._client = mock_client
    svc._current_provider = settings.AI_PROVIDER.lower()
    svc._current_key = settings.get_active_api_key()


@pytest.mark.asyncio
async def test_missing_api_key(clean_openai, monkeypatch):
    """Test behavior when the active provider key is completely missing."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)

    with pytest.raises(RuntimeError, match="API key is not set"):
        await clean_openai.chat("Hello")


@pytest.mark.asyncio
async def test_chat_rate_limit(clean_openai):
    """Test handling of RateLimitError during chat generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    resp = httpx.Response(429, request=req)
    mock_create.side_effect = RateLimitError("Rate limit", response=resp, body=None)
    mock_client.chat.completions.create = mock_create
    _install_client(clean_openai, mock_client)

    with pytest.raises(RuntimeError, match="Rate limit exceeded for"):
        await clean_openai.chat("Hello")


@pytest.mark.asyncio
async def test_chat_connection_error(clean_openai):
    """Test handling of APIConnectionError during chat generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    mock_create.side_effect = APIConnectionError(request=req)
    mock_client.chat.completions.create = mock_create
    _install_client(clean_openai, mock_client)

    with pytest.raises(RuntimeError, match="Cannot connect to"):
        await clean_openai.chat("Hello")


@pytest.mark.asyncio
async def test_chat_api_error(clean_openai):
    """Test handling of generic APIError during chat generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    mock_create.side_effect = APIError("API Error", request=req, body=None)
    mock_client.chat.completions.create = mock_create
    _install_client(clean_openai, mock_client)

    with pytest.raises(RuntimeError, match="API error:"):
        await clean_openai.chat("Hello")


@pytest.mark.asyncio
async def test_embed_api_error(clean_openai):
    """Test handling of APIError during embedding generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    mock_create.side_effect = APIError("API Error", request=req, body=None)
    mock_client.embeddings.create = mock_create
    _install_client(clean_openai, mock_client)

    with pytest.raises(RuntimeError, match="Failed to generate embedding"):
        await clean_openai.embed("text")


@pytest.mark.asyncio
async def test_chat_with_context(clean_openai):
    """Ensure context formatting logic works properly."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Mock answer"))]
    mock_client.chat.completions.create = mock_create
    _install_client(clean_openai, mock_client)

    answer = await clean_openai.chat("What?", context="Important context.")
    assert answer == "Mock answer"

    # Verify context was injected into the prompt
    args, kwargs = mock_create.call_args
    messages = kwargs["messages"]
    assert len(messages) == 2
    assert "Important context." in messages[1]["content"]
