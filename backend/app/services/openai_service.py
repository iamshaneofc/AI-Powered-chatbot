"""
services/openai_service.py — OpenAI API wrapper.

Responsibilities:
  - Chat completions (GPT-4o / GPT-3.5)
  - Text embeddings (text-embedding-3-small)
  - Async-first: uses openai.AsyncOpenAI
  - Centralised retry / error handling

Usage:
    from app.services.openai_service import openai_service
    answer  = await openai_service.chat("What is RAG?")
    vector  = await openai_service.embed("Some text to embed")
"""

from typing import Any

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIService:
    """Thin async wrapper around the OpenAI Python SDK."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not set in environment variables.")
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    # ── Chat completion ───────────────────────────────────────────────────
    async def chat(
        self,
        user_message: str,
        system_prompt: str = "You are a helpful AI assistant.",
        context: str | None = None,
        model: str | None = None,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            user_message:  The user's question.
            system_prompt: Instructions for the model's persona/behaviour.
            context:       Optional retrieved context prepended to the user message.
            model:         Override the default model.

        Returns:
            The assistant's reply as a plain string.
        """
        model = model or settings.OPENAI_MODEL

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        if context:
            messages.append({
                "role": "user",
                "content": (
                    f"Use the following context to answer the question.\n\n"
                    f"Context:\n{context}\n\n"
                    f"Question: {user_message}"
                ),
            })
        else:
            messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
            )
            answer = response.choices[0].message.content or ""
            logger.debug("GPT [%s] → %d chars", model, len(answer))
            return answer.strip()

        except RateLimitError as exc:
            logger.error("OpenAI rate limit hit: %s", exc)
            raise RuntimeError("OpenAI rate limit exceeded. Please retry later.") from exc
        except APIConnectionError as exc:
            logger.error("OpenAI connection error: %s", exc)
            raise RuntimeError("Cannot connect to OpenAI API.") from exc
        except APIError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise RuntimeError(f"OpenAI API error: {exc}") from exc

    # ── Embeddings ────────────────────────────────────────────────────────
    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """
        Generate a text embedding vector.

        Args:
            text:  The text to embed (will be truncated if too long).
            model: Override the default embedding model.

        Returns:
            A list of floats representing the embedding vector.
        """
        model = model or settings.OPENAI_EMBEDDING_MODEL

        # OpenAI recommends replacing newlines for best performance
        clean_text = text.replace("\n", " ").strip()

        try:
            response = await self.client.embeddings.create(
                model=model,
                input=clean_text,
            )
            vector = response.data[0].embedding
            logger.debug("Embedded %d chars → dim=%d", len(clean_text), len(vector))
            return vector

        except APIError as exc:
            logger.error("Embedding error: %s", exc)
            raise RuntimeError(f"Failed to generate embedding: {exc}") from exc

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Embed multiple texts in a single API call (more efficient)."""
        model = model or settings.OPENAI_EMBEDDING_MODEL
        cleaned = [t.replace("\n", " ").strip() for t in texts]

        response = await self.client.embeddings.create(model=model, input=cleaned)
        return [item.embedding for item in response.data]


# Singleton instance
openai_service = OpenAIService()
