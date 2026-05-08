from unittest.mock import patch

def test_summarize_endpoint(client, mock_openai):
    with patch("app.vectorstore.faiss_store.FAISSStore.get_document_text") as mock_get_docs:
        mock_get_docs.return_value = ["Mock text 1", "Mock text 2"]
        response = client.post(
            "/api/v1/summarize",
            json={"filename": "test.pdf", "summary_type": "brief"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Mocked LLM answer"
        assert data["summary_type"] == "brief"

def test_summarize_not_found(client):
    with patch("app.vectorstore.faiss_store.FAISSStore.get_document_text") as mock_get_docs:
        mock_get_docs.return_value = []
        response = client.post(
            "/api/v1/summarize",
            json={"filename": "missing.pdf"}
        )
        assert response.status_code == 404
