"""
services/vector_service.py — Document chunking, embedding, and FAISS indexing.

Acts as the bridge between:
  - Raw text (from documents / transcripts)
  - OpenAI embeddings
  - The FAISS vector store

Usage:
    from app.services.vector_service import vector_service

    await vector_service.add_text("Your document text here", metadata={"source": "file.pdf"})
    results = await vector_service.search("What is machine learning?", top_k=5)
"""

from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorService:
    """Orchestrates chunking → embedding → FAISS upsert / search."""

    # ── Text chunking ─────────────────────────────────────────────────────
    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        """
        Split text into overlapping chunks by character count.
        Simple but effective for most documents.
        """
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return [c.strip() for c in chunks if c.strip()]

    # ── Add documents ─────────────────────────────────────────────────────
    async def add_text(
        self,
        text: str,
        metadata: dict | None = None,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> int:
        """
        Chunk text, embed each chunk, and upsert into FAISS.

        Returns the number of chunks added.
        """
        chunk_size = chunk_size or settings.VECTOR_CHUNK_SIZE
        overlap    = overlap    or settings.VECTOR_CHUNK_OVERLAP

        chunks = self._chunk_text(text, chunk_size, overlap)
        if not chunks:
            logger.warning("add_text called with empty text — skipping.")
            return 0

        logger.info("Chunking text into %d pieces (size=%d, overlap=%d)", len(chunks), chunk_size, overlap)

        from app.services.openai_service import openai_service
        from app.vectorstore.faiss_store  import faiss_store

        # Embed all chunks in one batched API call
        vectors = await openai_service.embed_batch(chunks)

        # Build metadata per chunk
        metas = [
            {**(metadata or {}), "chunk_index": i, "chunk_total": len(chunks)}
            for i in range(len(chunks))
        ]

        faiss_store.add(vectors=vectors, texts=chunks, metadatas=metas)
        faiss_store.save()

        logger.info("✅  Added %d chunks to FAISS index", len(chunks))
        return len(chunks)

    # ── Similarity search ─────────────────────────────────────────────────
    async def search(self, query: str, top_k: int | None = None, filename_filter: str | None = None) -> list[dict]:
        """
        Embed the query and return the top-k most similar chunks.
        Optionally filters results by source filename.

        Returns a list of dicts:
          [{"text": ..., "score": ..., "metadata": ...}, ...]
        """
        top_k = top_k or settings.VECTOR_TOP_K

        from app.services.openai_service import openai_service
        from app.vectorstore.faiss_store  import faiss_store

        query_vector = await openai_service.embed(query)
        results = faiss_store.search(query_vector, top_k=top_k, filename_filter=filename_filter)

        logger.debug("FAISS search returned %d results for query: %s…", len(results), query[:60])
        return results


# Singleton
vector_service = VectorService()
