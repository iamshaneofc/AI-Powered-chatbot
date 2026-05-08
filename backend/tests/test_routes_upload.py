import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.routes.upload import _index_document, _transcribe_and_index
from pathlib import Path

def test_upload_pdf_invalid_ext(client):
    """Test 400 rejection for non-PDF files on the PDF endpoint."""
    response = client.post("/api/v1/upload/pdf", files={"file": ("test.txt", b"txt", "text/plain")})
    assert response.status_code == 400

def test_upload_pdf_empty_text(client):
    """Test 400 rejection when the PDF has no text (e.g. image only)."""
    with patch("app.utils.file_utils.validate_file"), \
         patch("app.utils.file_utils.save_upload", new_callable=AsyncMock), \
         patch("app.services.pdf_service.pdf_service.extract_text", return_value="   "):
        
        response = client.post("/api/v1/upload/pdf", files={"file": ("test.pdf", b"content", "application/pdf")})
        assert response.status_code == 400
        assert "No text could be extracted" in response.json()["detail"]

def test_upload_pdf_exception(client):
    """Test 500 exception handling during synchronous PDF upload."""
    with patch("app.routes.upload.validate_file", side_effect=Exception("Disk full")):
        response = client.post("/api/v1/upload/pdf", files={"file": ("test.pdf", b"content", "application/pdf")})
        assert response.status_code == 500
        assert "Disk full" in response.json()["detail"]

def test_upload_document_invalid_ext(client):
    """Test 400 rejection for unsupported background document types."""
    response = client.post("/api/v1/upload/document", files={"file": ("test.xyz", b"content", "text/plain")})
    assert response.status_code == 400

def test_upload_media_invalid_ext(client):
    """Test 400 rejection for unsupported background media types."""
    response = client.post("/api/v1/upload/media", files={"file": ("test.pdf", b"content", "application/pdf")})
    assert response.status_code == 400

def test_upload_media_empty_transcript(client):
    """Test 400 rejection when Whisper returns an empty transcript."""
    with patch("app.utils.file_utils.validate_file"), \
         patch("app.utils.file_utils.save_upload", new_callable=AsyncMock), \
         patch("app.services.whisper_service.whisper_service.transcribe_with_meta", new_callable=AsyncMock) as mock_t:
        
        mock_t.return_value = {"text": "   "}
        response = client.post("/api/v1/upload/media", files={"file": ("test.mp3", b"content", "audio/mpeg")})
        assert response.status_code == 400
        assert "Empty transcript" in response.json()["detail"]

def test_upload_media_exception(client):
    """Test 500 exception handling during synchronous media upload."""
    with patch("app.routes.upload.validate_file", side_effect=Exception("Transcribe error")):
        response = client.post("/api/v1/upload/media", files={"file": ("test.mp3", b"content", "audio/mpeg")})
        assert response.status_code == 500
        assert "Transcribe error" in response.json()["detail"]

@pytest.mark.asyncio
async def test_bg_index_document():
    """Test background task safely handles empty extraction."""
    with patch("app.routes.upload.extract_text", return_value="   "):
        await _index_document(Path("test.pdf")) # should safely log warning and return

    """Test background task safely handles extraction crashes."""
    with patch("app.routes.upload.extract_text", side_effect=Exception("bg err")):
        await _index_document(Path("test.pdf")) # should safely log error and return

@pytest.mark.asyncio
async def test_bg_transcribe_and_index():
    """Test background task safely handles empty Whisper output."""
    with patch("app.services.whisper_service.whisper_service.transcribe", new_callable=AsyncMock) as mock_t:
        mock_t.return_value = "   "
        await _transcribe_and_index(Path("test.mp3")) # warning

    """Test background task safely handles Whisper crashes."""
    with patch("app.services.whisper_service.whisper_service.transcribe", new_callable=AsyncMock) as mock_t:
        mock_t.side_effect = Exception("bg whisper err")
        await _transcribe_and_index(Path("test.mp3")) # error
