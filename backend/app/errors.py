"""Typed application errors.

Every failure the user can realistically hit has its own class with a stable
machine-readable `code`, an HTTP status, and a message written for a human.
`register_error_handlers` turns them into a consistent JSON envelope so the
React client never has to guess at the shape of a failure.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class PaperPilotError(Exception):
    """Base class for all expected failures."""

    status_code: int = 400
    code: str = "paperpilot_error"

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_payload(self) -> dict:
        payload = {"code": self.code, "message": self.message}
        if self.detail:
            payload["detail"] = self.detail
        return payload


# --- Upload / file validation -------------------------------------------


class UnsupportedFileTypeError(PaperPilotError):
    status_code = 415
    code = "unsupported_file_type"


class FileTooLargeError(PaperPilotError):
    status_code = 413
    code = "file_too_large"


class EmptyFileError(PaperPilotError):
    status_code = 400
    code = "empty_file"


class DuplicateDocumentError(PaperPilotError):
    status_code = 409
    code = "duplicate_document"


# --- PDF processing ------------------------------------------------------


class PDFExtractionError(PaperPilotError):
    status_code = 422
    code = "pdf_extraction_failed"


class NoExtractableTextError(PaperPilotError):
    status_code = 422
    code = "no_extractable_text"


# --- RAG components ------------------------------------------------------


class EmbeddingError(PaperPilotError):
    status_code = 502
    code = "embedding_failed"


class VectorStoreError(PaperPilotError):
    status_code = 500
    code = "vector_store_failed"


class LLMError(PaperPilotError):
    status_code = 502
    code = "llm_failed"


class MissingAPIKeyError(PaperPilotError):
    status_code = 503
    code = "missing_api_key"


class NoRelevantContextError(PaperPilotError):
    status_code = 404
    code = "no_relevant_context"


class DocumentNotFoundError(PaperPilotError):
    status_code = 404
    code = "document_not_found"


class InvalidQuestionError(PaperPilotError):
    status_code = 400
    code = "invalid_question"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PaperPilotError)
    async def handle_paperpilot_error(_: Request, exc: PaperPilotError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", []) if part != "body")
        message = first.get("msg", "The request body was not valid.")
        return JSONResponse(
            status_code=422,
            content={
                "code": "invalid_request",
                "message": f"{field or 'request'}: {message}",
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "message": "Something failed on the server. Check the backend logs for the traceback.",
                "detail": str(exc)[:300],
            },
        )
