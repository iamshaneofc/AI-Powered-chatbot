"""
services/openai_service.py — Multi-provider AI API wrapper.

Responsibilities:
  - Chat completions (supports multiple providers)
  - Text embeddings (provider-specific)
  - Async-first: uses openai.AsyncOpenAI
  - Centralised retry / error handling
  - Dynamic provider switching based on settings

Usage:
    from app.services.openai_service import openai_service
    answer  = await openai_service.chat("What is RAG?")
    vector  = await openai_service.embed("Some text to embed")
"""

from typing import Any, Optional

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIService:
    """Thin async wrapper around the OpenAI Python SDK with multi-provider support."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._current_provider: str | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client for the current provider."""
        current_provider = settings.AI_PROVIDER.lower()
        
        # Recreate client if provider changed
        if self._client is None or self._current_provider != current_provider:
            api_key = settings.get_active_api_key()
            base_url = settings.get_active_base_url()
            
            if not api_key:
                raise RuntimeError(
                    f"API key is not set for provider '{current_provider}'. "
                    f"Please configure it in Settings."
                )
            
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            self._current_provider = current_provider
            logger.info("Initialized client for provider: %s", current_provider)
        
        return self._client

    def _get_model(self, model: str | None = None) -> str:
        """Get the model to use, either provided or from settings."""
        if model:
            return model
        return settings.get_active_model()

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
        model = self._get_model(model)

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
            logger.error("Rate limit hit for provider %s: %s", settings.AI_PROVIDER, exc)
            raise RuntimeError(f"Rate limit exceeded for {settings.AI_PROVIDER}. Please retry later.") from exc
        except APIConnectionError as exc:
            logger.error("Connection error for provider %s: %s", settings.AI_PROVIDER, exc)
            raise RuntimeError(f"Cannot connect to {settings.AI_PROVIDER} API.") from exc
        except APIError as exc:
            logger.error("API error for provider %s: %s", settings.AI_PROVIDER, exc)
            raise RuntimeError(f"{settings.AI_PROVIDER} API error: {exc}") from exc

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
        # Get embedding model from provider config
        from app.config.providers import get_provider
        try:
            provider = get_provider(settings.AI_PROVIDER.lower())
            embedding_model = provider.embedding_model
        except ValueError:
            embedding_model = settings.OPENAI_EMBEDDING_MODEL
        
        if model:
            embedding_model = model

        # Clean text for better embeddings
        clean_text = text.replace("\n", " ").strip()

        try:
            response = await self.client.embeddings.create(
                model=embedding_model,
                input=clean_text,
            )
            vector = response.data[0].embedding
            logger.debug("Embedded %d chars → dim=%d", len(clean_text), len(vector))
            return vector

        except APIError as exc:
            logger.error("Embedding error for provider %s: %s", settings.AI_PROVIDER, exc)
            raise RuntimeError(f"Failed to generate embedding: {exc}") from exc

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Embed multiple texts in a single API call (more efficient)."""
        # Get embedding model from provider config
        from app.config.providers import get_provider
        try:
            provider = get_provider(settings.AI_PROVIDER.lower())
            embedding_model = provider.embedding_model
        except ValueError:
            embedding_model = settings.OPENAI_EMBEDDING_MODEL
        
        if model:
            embedding_model = model

        cleaned = [t.replace("\n", " ").strip() for t in texts]

        response = await self.client.embeddings.create(model=embedding_model, input=cleaned)
        return [item.embedding for item in response.data]


# Singleton instance
openai_service = OpenAIService()
