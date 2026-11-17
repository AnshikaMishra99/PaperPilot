"""/api/chat -- ask a question against the indexed papers.

Conversation state lives in the browser. The client sends the last few turns
with each question so follow-ups like "and its limitations?" can be resolved,
but nothing is stored server-side, so "Clear chat" is instant and needs no
endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import User, get_current_user
from ..errors import DocumentNotFoundError, InvalidQuestionError
from ..rag import pipeline
from ..schemas import AskRequest, AskResponse, SourceOut
from ..services import document_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    question = payload.question.strip()
    if not question:
        raise InvalidQuestionError("Type a question before sending.")
    if len(question) < 3:
        raise InvalidQuestionError("That question is too short to search on.")

    records = document_service.list_documents(user_id=current_user.id)
    if not records:
        raise InvalidQuestionError(
            "No papers are indexed yet in your account. Upload a PDF first, then ask about it."
        )

    known_ids = {record["id"] for record in records}
    document_ids = payload.document_ids or None
    if document_ids:
        unknown = [doc_id for doc_id in document_ids if doc_id not in known_ids]
        if unknown:
            raise DocumentNotFoundError(
                "Some selected papers no longer exist in your account. Refresh the document list and try again."
            )

    history = [(turn.role, turn.content) for turn in payload.history][-6:]

    result = pipeline.answer_question(
        question=question,
        mode=payload.mode,
        document_ids=document_ids,
        history=history,
        user_id=current_user.id,
    )

    sources = [
        SourceOut(
            label=source.label,
            document_id=source.chunk.document_id,
            filename=source.chunk.filename,
            page=source.chunk.page,
            chunk_id=source.chunk.chunk_id,
            score=source.chunk.score,
            excerpt=pipeline.source_excerpt(source.chunk),
        )
        for source in result.sources
    ]

    return AskResponse(
        answer=result.answer,
        mode=result.mode,
        sources=sources,
        grounded=result.grounded,
        documents_searched=len(document_ids) if document_ids else len(records),
    )
