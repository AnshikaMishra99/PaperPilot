"""Request and response models.

These are the contract between FastAPI and the React client. Field names here
match exactly what `frontend/src/api/client.js` reads.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ExplanationMode = Literal["simple", "technical"]


# --- Documents -----------------------------------------------------------


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: Literal["ready", "failed"]
    pages: int
    chunks: int
    size_bytes: int
    uploaded_at: str
    error: str | None = None


class UploadResultOut(BaseModel):
    filename: str
    success: bool
    document: DocumentOut | None = None
    error_code: str | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    uploaded: list[UploadResultOut]
    succeeded: int
    failed: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total_documents: int
    total_chunks: int


class DeleteResponse(BaseModel):
    id: str
    deleted: bool
    chunks_removed: int


# --- Chat ----------------------------------------------------------------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    mode: ExplanationMode = "simple"
    # Optional filter: restrict retrieval to these document ids.
    document_ids: list[str] | None = None
    # Last few turns, used only to resolve pronouns in follow-up questions.
    history: list[ChatTurn] = Field(default_factory=list, max_length=10)


class SourceOut(BaseModel):
    label: str
    document_id: str
    filename: str
    page: int
    chunk_id: str
    score: float
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    mode: ExplanationMode
    sources: list[SourceOut]
    grounded: bool
    documents_searched: int


# --- Misc ----------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok"]
    embedding_provider: str
    llm_model: str
    llm_configured: bool
    documents: int
    chunks: int
