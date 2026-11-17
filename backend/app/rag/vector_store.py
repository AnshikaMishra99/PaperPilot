"""Step 4 of ingestion and step 2 of querying: the vector database.

A normal database answers "which row equals this value". Here we need "which
passage *means* something close to this question", which is a nearest-neighbour
search over high-dimensional vectors. Chroma does that, stores the metadata
(filename, page, chunk id) next to each vector, and persists to a local folder
so nothing is lost when the server restarts.

Distance metric is cosine, so 0.0 means identical direction and larger numbers
mean less related. `max_distance` in settings is the cut-off above which we
declare "nothing relevant was found" rather than feeding the model noise.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import settings
from ..errors import VectorStoreError
from .chunker import Chunk

COLLECTION_NAME = "paperpilot_chunks"
UPSERT_BATCH = 128


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    text: str
    distance: float
    embedding: list[float] | None = None

    @property
    def score(self) -> float:
        """Distance turned into a 0-1 relevance score for display."""
        return round(max(0.0, 1.0 - self.distance), 3)


class VectorStore:
    def __init__(self) -> None:
        try:
            self._client = chromadb.PersistentClient(
                path=str(settings.chroma_path),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
            )
        except Exception as exc:
            raise VectorStoreError(
                "Could not open the vector database. Check that CHROMA_DIR is writable.",
                detail=str(exc)[:200],
            ) from exc

    def _get_collection(self, provider: str | None = None):
        prov = (provider or settings.embedding_provider).lower().strip()
        name = f"paperpilot_{prov}"
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    @property
    def _collection(self):
        return self._get_collection()

    # --- writes ----------------------------------------------------------

    def add_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunk count and embedding count did not match.")
        if not chunks:
            return

        col = self._collection
        try:
            for start in range(0, len(chunks), UPSERT_BATCH):
                batch = chunks[start : start + UPSERT_BATCH]
                try:
                    col.upsert(
                        ids=[chunk.chunk_id for chunk in batch],
                        embeddings=embeddings[start : start + UPSERT_BATCH],
                        documents=[chunk.text for chunk in batch],
                        metadatas=[chunk.metadata for chunk in batch],
                    )
                except Exception as exc:
                    # If dimension mismatch occurs on an empty collection, recreate it with the correct dimension
                    if "dimension" in str(exc).lower() and col.count() == 0:
                        prov = settings.embedding_provider.lower().strip()
                        self._client.delete_collection(f"paperpilot_{prov}")
                        col = self._collection
                        col.upsert(
                            ids=[chunk.chunk_id for chunk in batch],
                            embeddings=embeddings[start : start + UPSERT_BATCH],
                            documents=[chunk.text for chunk in batch],
                            metadatas=[chunk.metadata for chunk in batch],
                        )
                    else:
                        raise
        except Exception as exc:
            raise VectorStoreError(
                "Writing embeddings to the vector database failed.",
                detail=str(exc)[:200],
            ) from exc

    def delete_document(self, document_id: str) -> int:
        removed = 0
        for prov in ["google", "local"]:
            try:
                col = self._get_collection(prov)
                existing = col.get(where={"document_id": document_id}, include=[])
                ids = existing.get("ids", []) or []
                if ids:
                    col.delete(ids=ids)
                    removed += len(ids)
            except Exception:
                pass
        return removed

    # --- reads -----------------------------------------------------------

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
        include_embeddings: bool = True,
        user_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Top-K nearest neighbours, optionally restricted to some documents and user.

        "Top-K" simply means: return the K closest chunks. K trades recall
        against noise -- too small and the answer may be missing, too large and
        the prompt fills with irrelevant text that can mislead the model.
        """
        conditions: list[dict] = []
        if user_id:
            conditions.append({"user_id": user_id})
        if document_ids:
            if len(document_ids) == 1:
                conditions.append({"document_id": document_ids[0]})
            else:
                conditions.append({"document_id": {"$in": document_ids}})

        where: dict | None = None
        if len(conditions) == 1:
            where = conditions[0]
        elif len(conditions) > 1:
            where = {"$and": conditions}

        includes = ["documents", "metadatas", "distances"]
        if include_embeddings:
            includes.append("embeddings")

        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=max(1, top_k),
                where=where,
                include=includes,
            )
        except Exception as exc:
            raise VectorStoreError(
                "Similarity search failed in the vector database.",
                detail=str(exc)[:200],
            ) from exc

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        embeddings = (result.get("embeddings") or [[]])[0] if include_embeddings else None

        retrieved: list[RetrievedChunk] = []
        for i, (chunk_id, text, metadata, distance) in enumerate(zip(ids, documents, metadatas, distances)):
            metadata = metadata or {}
            # Support both page_number and page in metadata (1-indexed)
            page_val = metadata.get("page_number")
            if page_val is None:
                page_val = metadata.get("page", 1)
            page_num = max(1, int(page_val or 1))

            chunk_emb = embeddings[i] if embeddings is not None and i < len(embeddings) else None
            if chunk_emb is not None:
                try:
                    chunk_emb = [float(x) for x in chunk_emb]
                except Exception:
                    chunk_emb = None

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(metadata.get("document_id", "")),
                    filename=str(metadata.get("filename", "unknown.pdf")),
                    page=page_num,
                    chunk_index=int(metadata.get("chunk_index", 0) or 0),
                    text=text or "",
                    distance=float(distance),
                    embedding=chunk_emb,
                )
            )
        return retrieved

    def count(self) -> int:
        try:
            return int(self._collection.count())
        except Exception:
            return 0


_store: VectorStore | None = None
_store_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = VectorStore()
    return _store
