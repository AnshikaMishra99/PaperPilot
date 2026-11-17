"""Step 3 of ingestion (and step 1 of querying): text -> vector.

An embedding maps a piece of text to a list of floats positioned so that
texts with similar *meaning* sit close together. That is what lets "What
dataset did they train on?" retrieve a passage that says "experiments were run
over CIFAR-100" even though the two share almost no words.

Two providers are supported behind one interface:
  * google -- Gemini's text-embedding-004 over HTTPS. No model download, and
    it supports asymmetric task types (a document and a question get embedded
    slightly differently, which measurably improves retrieval).
  * local  -- sentence-transformers/all-MiniLM-L6-v2 on the host machine. Runs
    with no API key and no network, useful for offline demos.

Both are wrapped so callers only ever see `embed_documents` / `embed_query`.
"""

from __future__ import annotations

import threading
import time

from ..config import settings
from ..errors import EmbeddingError, MissingAPIKeyError

GOOGLE_BATCH_SIZE = 64
MAX_RETRIES = 3


class Embedder:
    """Lazily-initialised embedding client for the configured provider."""

    def __init__(self) -> None:
        self._provider = settings.embedding_provider.lower().strip()
        self._lock = threading.Lock()
        self._local_model = None
        self._google_ready = False

        if self._provider not in {"google", "local"}:
            raise EmbeddingError(
                f"EMBEDDING_PROVIDER must be 'google' or 'local', got '{self._provider}'."
            )

    # --- public API ------------------------------------------------------

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return (
            settings.google_embedding_model
            if self._provider == "google"
            else settings.local_embedding_model
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._provider == "google":
            return self._embed_google(texts, task_type="retrieval_document")
        return self._embed_local(texts)

    def embed_query(self, text: str) -> list[float]:
        if self._provider == "google":
            return self._embed_google([text], task_type="retrieval_query")[0]
        return self._embed_local([text])[0]

    # --- google ----------------------------------------------------------

    def _ensure_google(self):
        import google.generativeai as genai

        if not self._google_ready:
            with self._lock:
                if not self._google_ready:
                    if not settings.google_api_key:
                        raise MissingAPIKeyError(
                            "GOOGLE_API_KEY is not set. Add it to backend/.env, or set "
                            "EMBEDDING_PROVIDER=local to embed without an API key."
                        )
                    try:
                        genai.configure(api_key=settings.google_api_key, transport="rest")
                    except Exception:
                        genai.configure(api_key=settings.google_api_key)
                    self._google_ready = True
        return genai

    def _embed_google(self, texts: list[str], task_type: str) -> list[list[float]]:
        try:
            genai = self._ensure_google()
            vectors: list[list[float]] = []
            models_to_try = [
                settings.google_embedding_model,
                "models/gemini-embedding-001",
                "models/gemini-embedding-2",
                "models/text-embedding-004",
            ]
            # Deduplicate
            candidate_models = []
            for m in models_to_try:
                if m and m not in candidate_models:
                    candidate_models.append(m)

            current_model_idx = 0
            for start in range(0, len(texts), GOOGLE_BATCH_SIZE):
                batch = texts[start : start + GOOGLE_BATCH_SIZE]
                last_error: Exception | None = None

                for attempt in range(MAX_RETRIES):
                    model_to_use = candidate_models[current_model_idx]
                    try:
                        response = genai.embed_content(
                            model=model_to_use,
                            content=batch,
                            task_type=task_type,
                        )
                        embedding = response["embedding"]
                        if embedding and isinstance(embedding[0], (int, float)):
                            embedding = [embedding]
                        vectors.extend([list(map(float, vector)) for vector in embedding])
                        break
                    except Exception as exc:
                        last_error = exc
                        err_str = str(exc).lower()
                        # If model not found or not supported, rotate candidate
                        if ("not found" in err_str or "not supported" in err_str) and current_model_idx + 1 < len(candidate_models):
                            current_model_idx += 1
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(1.0 * (attempt + 1))
                else:
                    raise last_error or Exception("Google embedding rejected request.")

            if len(vectors) == len(texts):
                return vectors
            raise EmbeddingError("Google embedding returned incomplete vector batch.")
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                "The embedding service rejected the request. Check your GOOGLE_API_KEY and your quota, then try again.",
                detail=str(exc)[:200],
            ) from exc

    # --- local -----------------------------------------------------------

    def _ensure_local(self):
        if self._local_model is None:
            with self._lock:
                if self._local_model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                        self._local_model = SentenceTransformer(settings.local_embedding_model)
                    except Exception:
                        try:
                            from chromadb.utils import embedding_functions
                            self._local_model = embedding_functions.DefaultEmbeddingFunction()
                        except Exception as exc:
                            raise EmbeddingError(
                                "Could not initialize local embedding model. "
                                "Install sentence-transformers or ensure chromadb is installed.",
                                detail=str(exc)[:200],
                            ) from exc
        return self._local_model

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_local()
        try:
            if hasattr(model, "encode"):
                vectors = model.encode(
                    texts,
                    batch_size=32,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return [list(map(float, vector)) for vector in vectors]
            else:
                vectors = model(texts)
                return [list(map(float, vector)) for vector in vectors]
        except Exception as exc:
            raise EmbeddingError(
                "The local embedding model failed while encoding text.",
                detail=str(exc)[:200],
            ) from exc


_embedder: Embedder | None = None
_embedder_lock = threading.Lock()


def reset_embedder() -> None:
    global _embedder
    with _embedder_lock:
        _embedder = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                _embedder = Embedder()
    return _embedder
