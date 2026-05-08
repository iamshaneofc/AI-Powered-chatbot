import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app

def test_transcribe_saved_missing_file(client):
    """Test HTTP 404 response when file doesn't exist."""
    response = client.post("/api/v1/transcribe", json={"filename": "does_not_exist.mp3"})
    assert response.status_code == 404
    assert "not found in upload directory" in response.json()["detail"]

def test_transcribe_saved_invalid_ext(client):
    """Test HTTP 400 response for unsupported extensions."""
    with patch("pathlib.Path.exists", return_value=True):
        response = client.post("/api/v1/transcribe", json={"filename": "test.txt"})
        assert response.status_code == 400
        assert "audio/video type" in response.json()["detail"]

def test_transcribe_saved_failure(client):
    """Test 500 fallback when Whisper transcription blows up internally."""
    with patch("pathlib.Path.exists", return_value=True), \
         patch("app.services.whisper_service.whisper_service.transcribe_with_meta", new_callable=AsyncMock) as mock_t:
        
        mock_t.side_effect = Exception("Whisper engine crashed")
        response = client.post("/api/v1/transcribe", json={"filename": "test.mp3"})
        
        assert response.status_code == 500
        assert "Whisper engine crashed" in response.json()["detail"]

def test_transcribe_upload_invalid_ext(client):
    """Test 400 response for unsupported upload extension."""
    response = client.post(
        "/api/v1/transcribe/upload",
        files={"file": ("test.txt", b"content", "text/plain")}
    )
    assert response.status_code == 400
    assert "Expected audio/video" in response.json()["detail"]

def test_transcribe_upload_failure(client):
    """Test 500 response when single-shot upload & transcribe fails."""
    with patch("app.utils.file_utils.validate_file"), \
         patch("app.utils.file_utils.save_upload", new_callable=AsyncMock) as mock_save, \
         patch("app.services.whisper_service.whisper_service.transcribe_with_meta", new_callable=AsyncMock) as mock_t:
        
        mock_save.return_value = MagicMock(name="test.mp3")
        mock_t.side_effect = Exception("Whisper failed on upload")
        
        response = client.post(
            "/api/v1/transcribe/upload",
            files={"file": ("test.mp3", b"content", "audio/mpeg")}
        )
        assert response.status_code == 500
        assert "Whisper failed on upload" in response.json()["detail"]
