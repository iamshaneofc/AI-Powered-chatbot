import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from openai import APIError, RateLimitError, APIConnectionError
import httpx
from app.services.openai_service import OpenAIService

@pytest.fixture
def clean_openai():
    """Returns a fresh instance of OpenAIService to prevent state leakage."""
    return OpenAIService()

def test_missing_api_key(clean_openai, monkeypatch):
    """Test behavior when OPENAI_API_KEY is completely missing."""
    # Temporarily remove the key from the environment and settings
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.config import settings
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        _ = clean_openai.client

@pytest.mark.asyncio
async def test_chat_rate_limit(clean_openai):
    """Test handling of RateLimitError during chat generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    resp = httpx.Response(429, request=req)
    mock_create.side_effect = RateLimitError("Rate limit", response=resp, body=None)
    mock_client.chat.completions.create = mock_create
    clean_openai._client = mock_client
    
    with pytest.raises(RuntimeError, match="OpenAI rate limit exceeded"):
        await clean_openai.chat("Hello")

@pytest.mark.asyncio
async def test_chat_connection_error(clean_openai):
    """Test handling of APIConnectionError during chat generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    mock_create.side_effect = APIConnectionError(request=req)
    mock_client.chat.completions.create = mock_create
    clean_openai._client = mock_client
    
    with pytest.raises(RuntimeError, match="Cannot connect to OpenAI API"):
        await clean_openai.chat("Hello")

@pytest.mark.asyncio
async def test_chat_api_error(clean_openai):
    """Test handling of generic APIError during chat generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    mock_create.side_effect = APIError("API Error", request=req, body=None)
    mock_client.chat.completions.create = mock_create
    clean_openai._client = mock_client
    
    with pytest.raises(RuntimeError, match="OpenAI API error:"):
        await clean_openai.chat("Hello")

@pytest.mark.asyncio
async def test_embed_api_error(clean_openai):
    """Test handling of APIError during embedding generation."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    req = httpx.Request("GET", "http://test")
    mock_create.side_effect = APIError("API Error", request=req, body=None)
    mock_client.embeddings.create = mock_create
    clean_openai._client = mock_client
    
    with pytest.raises(RuntimeError, match="Failed to generate embedding"):
        await clean_openai.embed("text")

@pytest.mark.asyncio
async def test_chat_with_context(clean_openai):
    """Ensure context formatting logic works properly."""
    mock_client = MagicMock()
    mock_create = AsyncMock()
    mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Mock answer"))]
    mock_client.chat.completions.create = mock_create
    clean_openai._client = mock_client
    
    answer = await clean_openai.chat("What?", context="Important context.")
    assert answer == "Mock answer"
    
    # Verify context was injected into the prompt
    args, kwargs = mock_create.call_args
    messages = kwargs["messages"]
    assert len(messages) == 2
    assert "Important context." in messages[1]["content"]
