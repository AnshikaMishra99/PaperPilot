"""/api/documents -- upload, list and delete papers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from ..auth import User, get_current_user
from ..config import settings
from ..errors import PaperPilotError
from ..schemas import (
    DeleteResponse,
    DocumentListResponse,
    DocumentOut,
    UploadResponse,
    UploadResultOut,
)
from ..services import document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILES_PER_REQUEST = 10


def _to_out(record: dict) -> DocumentOut:
    return DocumentOut(
        id=record["id"],
        filename=record["filename"],
        status=record.get("status", "ready"),
        pages=int(record.get("pages", 0)),
        chunks=int(record.get("chunks", 0)),
        size_bytes=int(record.get("size_bytes", 0)),
        uploaded_at=record["uploaded_at"],
        error=record.get("error"),
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    """Ingest one or more PDFs scoped to the authenticated user.

    Each file is processed independently: one bad PDF in a batch of five does
    not stop the other four, and the response reports per-file outcomes.
    """
    if not files:
        raise PaperPilotError("No files were included in the request.")
    if len(files) > MAX_FILES_PER_REQUEST:
        raise PaperPilotError(
            f"Too many files at once. Upload up to {MAX_FILES_PER_REQUEST} PDFs per batch."
        )

    results: list[UploadResultOut] = []

    for upload in files:
        filename = upload.filename or "untitled.pdf"
        try:
            content = await upload.read()
            record = document_service.add_document(
                filename=filename,
                content=content,
                user_id=current_user.id,
            )
            results.append(
                UploadResultOut(filename=filename, success=True, document=_to_out(record))
            )
        except PaperPilotError as exc:
            results.append(
                UploadResultOut(
                    filename=filename,
                    success=False,
                    error_code=exc.code,
                    error=exc.message,
                )
            )
        except Exception as exc:
            results.append(
                UploadResultOut(
                    filename=filename,
                    success=False,
                    error_code="internal_error",
                    error=f"Processing failed unexpectedly: {str(exc)[:160]}",
                )
            )
        finally:
            await upload.close()

    succeeded = sum(1 for result in results if result.success)
    return UploadResponse(
        uploaded=results,
        succeeded=succeeded,
        failed=len(results) - succeeded,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """List research papers uploaded by the currently authenticated user."""
    records = document_service.list_documents(user_id=current_user.id)
    return DocumentListResponse(
        documents=[_to_out(record) for record in records],
        total_documents=len(records),
        total_chunks=sum(int(record.get("chunks", 0)) for record in records),
    )


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
) -> DeleteResponse:
    """Remove a paper belonging to the current user."""
    removed = document_service.delete_document(document_id, user_id=current_user.id)
    return DeleteResponse(id=document_id, deleted=True, chunks_removed=removed)


@router.get("/limits")
async def upload_limits() -> dict:
    """Small helper the upload screen uses to show accurate limits."""
    return {
        "max_upload_mb": settings.max_upload_mb,
        "max_files_per_request": MAX_FILES_PER_REQUEST,
        "accepted_types": [".pdf"],
    }
