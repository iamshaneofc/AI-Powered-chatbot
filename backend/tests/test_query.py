"""
tests/test_query.py — Tests for the /query endpoints.

Mocks OpenAI + FAISS so tests run without real API keys or indexes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# RAG query
# ---------------------------------------------------------------------------
def test_query_requires_question():
    """Missing 'question' field should return 422."""
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == 422


def test_query_question_too_short():
    response = client.post("/api/v1/chat", json={"question": "ab"})
    assert response.status_code == 422


@patch("app.services.rag_service.RAGService.answer", new_callable=AsyncMock)
def test_query_success(mock_answer):
    mock_answer.return_value = {
        "answer":  "Machine learning is a subset of AI.",
        "sources": ["doc.pdf"],
        "model":   "gpt-4o",
        "chunks":  [],
    }

    response = client.post("/api/v1/chat", json={"question": "What is machine learning?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Machine learning is a subset of AI."
    assert "sources" in data
    assert "timestamp" in data


# ---------------------------------------------------------------------------
# Direct query
# ---------------------------------------------------------------------------
@patch("app.services.openai_service.OpenAIService.chat", new_callable=AsyncMock)
def test_direct_query_success(mock_chat):
    mock_chat.return_value = "Paris is the capital of France."

    response = client.post(
        "/api/v1/query/direct",
        json={"question": "What is the capital of France?"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Paris is the capital of France."


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
def test_history_endpoint_returns_list():
    response = client.get("/api/v1/query/history")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)


def test_history_limit_param():
    response = client.get("/api/v1/query/history?limit=3")
    assert response.status_code == 200
    assert len(response.json()["history"]) <= 3
