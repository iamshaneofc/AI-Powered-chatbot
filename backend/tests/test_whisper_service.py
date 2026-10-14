import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

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


def _mock_client(response):
    """Build a mock SDK client whose transcription call returns `response`."""
    client = MagicMock()
    create = AsyncMock()
    create.return_value = response
    client.audio.transcriptions.create = create
    return client, create


@pytest.fixture
def audio_file(tmp_path) -> Path:
    path = tmp_path / "test.mp3"
    path.write_bytes(b"dummy audio bytes")
    return path


def _force_api_backend(monkeypatch):
    """Make the service take the OpenAI Whisper API branch deterministically."""
    from types import SimpleNamespace
    import app.services.whisper_service as whisper_module

    monkeypatch.setattr(whisper_module, "settings", SimpleNamespace(
        WHISPER_BACKEND="api",
        OPENAI_API_KEY="sk-test-not-a-router-key",
        WHISPER_MODEL="base",
    ))


@pytest.mark.asyncio
async def test_transcribe(audio_file, monkeypatch):
    """Test basic transcription returning just a string."""
    from app.services.openai_service import openai_service
    _force_api_backend(monkeypatch)
    client, create = _mock_client(MockTranscriptionResponse("This is a transcript."))

    with patch.object(openai_service, "get_client", new=AsyncMock(return_value=client)):
        result = await whisper_service.transcribe(audio_file)

        assert result == "This is a transcript."
        create.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_with_meta(audio_file, monkeypatch):
    """Test transcription with full metadata and timestamp extraction."""
    from app.services.openai_service import openai_service
    _force_api_backend(monkeypatch)
    mock_resp = MockTranscriptionResponse(
        text="This is a transcript with meta.",
        language="en",
        duration=5.5,
        segments=[MockSegment(0.0, 5.5, "This is a transcript with meta.")]
    )
    client, create = _mock_client(mock_resp)

    with patch.object(openai_service, "get_client", new=AsyncMock(return_value=client)):
        result = await whisper_service.transcribe_with_meta(audio_file)

        assert result["text"] == "This is a transcript with meta."
        assert result["language"] == "en"
        assert result["duration"] == 5.5
        assert len(result["segments"]) == 1
        assert result["segments"][0]["start"] == 0.0


@pytest.mark.asyncio
async def test_transcribe_falls_back_to_local(audio_file, monkeypatch):
    """Without the local faster-whisper package, tests run the local branch mocked."""
    from app.services.openai_service import openai_service
    _force_api_backend(monkeypatch)
    client, create = _mock_client("API transcript")
    local_result = {
        "text": "Local transcript",
        "language": "en",
        "duration": 3.0,
        "segments": [{"start": 0.0, "end": 3.0, "text": "Local transcript"}],
    }

    with patch.object(openai_service, "get_client", new=AsyncMock(return_value=client)), \
         patch.object(whisper_service, "_transcribe_local", return_value=local_result) as mock_local:
        create.side_effect = RuntimeError("API unavailable")
        result = await whisper_service.transcribe_with_meta(audio_file)

    assert result["text"] == "Local transcript"
    mock_local.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_skips_api_for_oversized_file(tmp_path, monkeypatch):
    """Files above the 25MB API limit fall back to local transcription."""
    from app.services.openai_service import openai_service
    _force_api_backend(monkeypatch)
    huge = tmp_path / "huge.mp3"
    huge.write_bytes(b"x")
    client, create = _mock_client("should not be used")
    local_result = {"text": "Local transcript", "language": "en", "duration": 1.0, "segments": []}

    with patch.object(openai_service, "get_client", new=AsyncMock(return_value=client)), \
         patch.object(whisper_service, "_transcribe_local", return_value=local_result) as mock_local:
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 30 * 1024 * 1024
            result = await whisper_service.transcribe(huge)

    assert result == "Local transcript"
    create.assert_not_called()
    mock_local.assert_called_once()
