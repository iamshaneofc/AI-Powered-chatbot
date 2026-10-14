"""
vectorstore/faiss_store.py — FAISS vector index manager.

Wraps Meta's FAISS library with:
  - Persistent save / load to disk
  - Thread-safe add and search operations
  - Simple in-memory docstore (text + metadata per vector)

The index is an IndexFlatIP (inner-product / cosine similarity).
Vectors are L2-normalised before insertion so cosine ≈ inner-product.

Usage:
    from app.vectorstore.faiss_store import faiss_store

    faiss_store.add(vectors=[[0.1, 0.2, ...]], texts=["chunk"], metadatas=[{"source": "doc.pdf"}])
    results = faiss_store.search(query_vector=[0.1, 0.2, ...], top_k=5)
    faiss_store.save()
"""

import json
import threading
from pathlib import Path

import numpy as np

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_INDEX_FILE   = Path(settings.FAISS_INDEX_PATH).with_suffix(".index")
_DOCSTORE_FILE = Path(settings.FAISS_INDEX_PATH).with_suffix(".json")


class FAISSStore:
    """Thread-safe FAISS index with an attached in-memory docstore."""

    def __init__(self) -> None:
        # RLock so public helpers (load/search) can re-enter the same guard
        self._lock = threading.RLock()
        self._index = None          # faiss.Index
        self._texts: list[str] = []
        self._metadatas: list[dict] = []
        self._dim: int | None = None
        self._loaded_mtime: float | None = None   # mtime of the index file we last loaded/saved

    # ── Initialisation ────────────────────────────────────────────────────
    def _init_index(self, dim: int) -> None:
        """Create a new inner-product index (cosine after normalisation)."""
        import faiss
        self._dim = dim
        self._index = faiss.IndexFlatIP(dim)
        logger.info("Created new FAISS IndexFlatIP (dim=%d)", dim)

    # ── Persistence ───────────────────────────────────────────────────────
    @staticmethod
    def _file_mtime() -> float | None:
        """mtime of the index file on disk, or None if it doesn't exist."""
        try:
            return _INDEX_FILE.stat().st_mtime
        except OSError:
            return None

    def save(self) -> None:
        """Persist the index and docstore to disk."""
        if self._index is None:
            return
        import faiss
        with self._lock:
            _INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Docstore first, index last: a concurrent reader that sees the new
            # index mtime is guaranteed to find the matching docstore.
            _DOCSTORE_FILE.write_text(
                json.dumps({"texts": self._texts, "metadatas": self._metadatas}),
                encoding="utf-8",
            )
            faiss.write_index(self._index, str(_INDEX_FILE))
            self._loaded_mtime = self._file_mtime()
        logger.info("FAISS index saved (%d vectors)", self._index.ntotal)

    def load(self) -> None:
        """Load the index and docstore from disk (if they exist)."""
        import faiss
        with self._lock:
            if not _INDEX_FILE.exists():
                # Another worker may have cleared it — drop stale in-memory data
                # so this process reports "empty" instead of serving ghost chunks.
                self._index = None
                self._texts = []
                self._metadatas = []
                self._dim = None
                self._loaded_mtime = None
                logger.info(
                    "No existing FAISS index found at %s — will create on first upload",
                    _INDEX_FILE,
                )
                return

            index = faiss.read_index(str(_INDEX_FILE))
            dim = index.d
            if _DOCSTORE_FILE.exists():
                data = json.loads(_DOCSTORE_FILE.read_text(encoding="utf-8"))
                texts     = data.get("texts", [])
                metadatas = data.get("metadatas", [])
            else:
                texts, metadatas = [], []

            # Commit only after everything parsed successfully
            self._index = index
            self._dim = dim
            self._texts = texts
            self._metadatas = metadatas
            self._loaded_mtime = self._file_mtime()
        logger.info("Loaded FAISS index: %d vectors (dim=%d)", self._index.ntotal, self._dim)

    def _reload_if_stale(self) -> None:
        """
        Re-read the index from disk when another process has modified it.

        Keeps every uvicorn worker (and every restart) seeing the same
        knowledge base instead of a stale in-memory snapshot.
        """
        with self._lock:
            if self._file_mtime() == self._loaded_mtime:
                return
            try:
                self.load()
            except Exception as exc:
                # Another worker may be mid-write; keep serving current data
                # and retry on the next call.
                logger.warning("Could not reload FAISS index (will retry): %s", exc)

    # ── Mutation ──────────────────────────────────────────────────────────
    def add(
        self,
        vectors: list[list[float]],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        Add vectors to the index alongside their source texts and metadata.

        Vectors are L2-normalised (converts IP to cosine similarity).
        """
        if not vectors:
            return

        arr = np.array(vectors, dtype="float32")
        # L2 normalise so inner-product == cosine similarity
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        arr /= norms

        with self._lock:
            if self._index is None:
                self._init_index(arr.shape[1])
            self._index.add(arr)
            self._texts.extend(texts)
            self._metadatas.extend(metadatas)

        logger.debug("Added %d vectors — index total: %d", len(vectors), self._index.ntotal)

    # ── Search ────────────────────────────────────────────────────────────
    def search(self, query_vector: list[float], top_k: int = 5, filename_filter: str | None = None) -> list[dict]:
        """
        Find the top-k most similar chunks for the given query vector.
        Optionally filters results by source filename.

        Returns:
            [{"text": ..., "score": float, "metadata": {...}}, ...]
        """
        self._reload_if_stale()

        if self._index is None or self._index.ntotal == 0:
            return []

        arr = np.array([query_vector], dtype="float32")
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        arr /= np.where(norms == 0, 1, norms)

        # If filtering by filename, we may need to retrieve more results
        # initially to ensure we get enough matches after filtering.
        # For this implementation, we search the entire index if filtered,
        # as it's a Flat index and ntotal is typically small (< 100k).
        search_k = self._index.ntotal if filename_filter else min(top_k, self._index.ntotal)

        try:
            with self._lock:
                scores, indices = self._index.search(arr, search_k)
        except Exception as exc:
            # Dimension mismatch (index built with a different embedding model)
            # or a partially written file from another worker.
            logger.error(
                "FAISS search failed (index dim=%s, query dim=%s): %s",
                self._dim, arr.shape[1], exc,
            )
            return []

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            
            meta = self._metadatas[idx] if idx < len(self._metadatas) else {}
            
            # Apply filename filter
            if filename_filter and meta.get("source") != filename_filter:
                continue

            results.append({
                "text":     self._texts[idx],
                "score":    float(score),
                "metadata": meta,
            })
            
            # Stop once we have enough results
            if len(results) >= top_k:
                break

        return results

    def get_document_text(self, filename: str) -> list[str]:
        """
        Retrieve all stored texts that belong to a specific source filename.
        Useful for summarization.
        """
        self._reload_if_stale()
        if not self._metadatas:
            return []
            
        with self._lock:
            # Reconstruct document using the chunk index to maintain order
            chunks_with_index = []
            for i, meta in enumerate(self._metadatas):
                if meta.get("source") == filename:
                    chunks_with_index.append((meta.get("chunk_index", 0), self._texts[i]))
            
            # Sort by chunk_index to keep original order
            chunks_with_index.sort(key=lambda x: x[0])
            return [text for _, text in chunks_with_index]

    # ── Helpers ───────────────────────────────────────────────────────────
    def is_ready(self) -> bool:
        self._reload_if_stale()
        return self._index is not None and self._index.ntotal > 0

    @property
    def total_vectors(self) -> int:
        self._reload_if_stale()
        return self._index.ntotal if self._index else 0

    @property
    def sources(self) -> list[str]:
        """Unique source filenames currently in the index, in index order."""
        self._reload_if_stale()
        seen: list[str] = []
        with self._lock:
            for meta in self._metadatas:
                source = meta.get("source", "unknown")
                if source not in seen:
                    seen.append(source)
        return seen

    # LangChain compatibility shims (used in rag_service.answer_with_langchain)
    @property
    def index(self):
        return self._index

    @property
    def docstore(self):
        return self._texts  # LangChain wrapper expects this

    @property
    def index_to_docstore_id(self):
        return {i: i for i in range(len(self._texts))}

    # ── Reset ─────────────────────────────────────────────────────────────
    def clear(self) -> None:
        """Reset the index and docstore, and delete files from disk."""
        with self._lock:
            self._index = None
            self._texts = []
            self._metadatas = []
            self._dim = None
            self._loaded_mtime = None
            
            if _INDEX_FILE.exists():
                _INDEX_FILE.unlink()
            if _DOCSTORE_FILE.exists():
                _DOCSTORE_FILE.unlink()
        
        logger.info("FAISS index and docstore cleared")


# Singleton
faiss_store = FAISSStore()
