import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, mock_open, MagicMock

from app.services.whisper_service import whisper_service

class MockSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text

class MockTranscriptionResponse:
    def __init__(self, text, language="en", duration=10.0, segments=None):
        self.text = text
        self.language = language
        self.duration = duration
        self.segments = segments or []
        
    def strip(self):
        return self.text.strip()

@pytest.mark.asyncio
async def test_transcribe():
    """Test basic transcription returning just a string."""
    mock_resp = "This is a transcript."
    
    from app.services.openai_service import openai_service
    mock_client = MagicMock()
    mock_create = AsyncMock()
    mock_create.return_value = mock_resp
    mock_client.audio.transcriptions.create = mock_create
    
    with patch("builtins.open", mock_open(read_data=b"dummy audio")), \
         patch.object(openai_service, "_client", mock_client):
        
        result = await whisper_service.transcribe(Path("test.mp3"))
        
        assert result == "This is a transcript."
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_transcribe_with_meta():
    """Test transcription with full metadata and timestamp extraction."""
    mock_resp = MockTranscriptionResponse(
        text="This is a transcript with meta.",
        language="en",
        duration=5.5,
        segments=[MockSegment(0.0, 5.5, "This is a transcript with meta.")]
    )
    
    from app.services.openai_service import openai_service
    mock_client = MagicMock()
    mock_create = AsyncMock()
    mock_create.return_value = mock_resp
    mock_client.audio.transcriptions.create = mock_create
    
    with patch("builtins.open", mock_open(read_data=b"dummy audio")), \
         patch.object(openai_service, "_client", mock_client):
        
        result = await whisper_service.transcribe_with_meta(Path("test.mp3"))
        
        assert result["text"] == "This is a transcript with meta."
        assert result["language"] == "en"
        assert result["duration"] == 5.5
        assert len(result["segments"]) == 1
        assert result["segments"][0]["start"] == 0.0
