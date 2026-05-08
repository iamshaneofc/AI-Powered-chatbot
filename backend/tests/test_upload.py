import io

def test_upload_pdf(client, mock_openai, mock_pdf_extract):
    file_content = b"fake pdf content"
    response = client.post(
        "/api/v1/upload/pdf",
        files={"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert "metadata" in data
    assert data["chunks"] > 0

def test_upload_invalid_file(client):
    file_content = b"fake content"
    response = client.post(
        "/api/v1/upload/pdf",
        files={"file": ("test.xyz", io.BytesIO(file_content), "text/plain")}
    )
    assert response.status_code == 400

def test_upload_media(client, mock_whisper, mock_openai):
    file_content = b"fake mp3 content"
    response = client.post(
        "/api/v1/upload/media",
        files={"file": ("test.mp3", io.BytesIO(file_content), "audio/mpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.mp3"
    assert "timestamps" in data
    assert len(data["timestamps"]) > 0
