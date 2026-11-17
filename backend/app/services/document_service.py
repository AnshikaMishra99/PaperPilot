"""Document management: validation, the registry, and delete.

The vector store holds chunks. This service holds the *paper-level* record the
UI lists -- filename, page count, chunk count, upload time -- in a small JSON
file. A JSON registry is enough for a single-user local app and avoids adding a
second database that would have to be explained without earning its place.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings
from ..errors import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from ..rag.pipeline import ingest_pdf
from ..rag.vector_store import get_vector_store

PDF_MAGIC = b"%PDF-"
_registry_lock = threading.Lock()


# --- validation ----------------------------------------------------------


def validate_upload(filename: str, content: bytes) -> None:
    """Reject anything that is not a reasonable PDF before doing real work."""
    if not filename.lower().endswith(".pdf"):
        raise UnsupportedFileTypeError(
            f"{filename} is not a PDF. PaperPilot only accepts .pdf files."
        )
    if not content:
        raise EmptyFileError(f"{filename} is empty (0 bytes).")
    if len(content) > settings.max_upload_bytes:
        size_mb = len(content) / (1024 * 1024)
        raise FileTooLargeError(
            f"{filename} is {size_mb:.1f} MB. The limit is {settings.max_upload_mb} MB."
        )
    # Extension alone is trivially spoofed; check the file signature too.
    if not content.lstrip()[:5].startswith(PDF_MAGIC):
        raise UnsupportedFileTypeError(
            f"{filename} has a .pdf extension but its contents are not a PDF."
        )


# --- registry ------------------------------------------------------------


def _registry_file() -> Path:
    return settings.registry_file


def _read_registry() -> list[dict]:
    path = _registry_file()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # A corrupt registry should not brick the app.
        return []


def _write_registry(records: list[dict]) -> None:
    path = _registry_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)
    temp.replace(path)


def list_documents(user_id: str | None = None) -> list[dict]:
    records = _read_registry()
    if user_id:
        records = [r for r in records if r.get("user_id") == user_id]
    return sorted(records, key=lambda record: record["uploaded_at"], reverse=True)


def get_document(document_id: str, user_id: str | None = None) -> dict:
    for record in _read_registry():
        if record["id"] == document_id:
            if user_id and record.get("user_id") and record.get("user_id") != user_id:
                raise DocumentNotFoundError(f"No document with id {document_id} found for this account.")
            return record
    raise DocumentNotFoundError(f"No document with id {document_id}.")


def total_chunks(user_id: str | None = None) -> int:
    records = list_documents(user_id)
    return sum(int(record.get("chunks", 0)) for record in records)


# --- ingestion -----------------------------------------------------------


def add_document(filename: str, content: bytes, user_id: str = "") -> dict:
    """Validate, de-duplicate, ingest, and record one PDF for a specific user."""
    validate_upload(filename, content)

    checksum = hashlib.sha256(content).hexdigest()
    with _registry_lock:
        for record in _read_registry():
            # Deduplicate per user (different users may upload the same paper)
            if record.get("checksum") == checksum and (not user_id or record.get("user_id") == user_id):
                raise DuplicateDocumentError(
                    f"{filename} is already uploaded as \"{record['filename']}\". "
                    "Delete it first if you want to re-index it."
                )

    document_id = uuid.uuid4().hex[:12]
    stored_path = settings.upload_path / f"{document_id}.pdf"

    try:
        result = ingest_pdf(pdf_bytes=content, filename=filename, document_id=document_id, user_id=user_id)
    except Exception:
        # Ingestion is only "done" once embeddings are stored. If any stage
        # failed, remove whatever partial vectors were written.
        try:
            get_vector_store().delete_document(document_id)
        except Exception:
            pass
        raise

    try:
        stored_path.write_bytes(content)
    except OSError:
        stored_path = None  # type: ignore[assignment]

    record = {
        "id": document_id,
        "filename": filename,
        "status": "ready",
        "pages": result.pages,
        "chunks": result.chunks,
        "size_bytes": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checksum": checksum,
        "user_id": user_id,
        "stored_path": str(stored_path) if stored_path else None,
        "error": None,
    }

    with _registry_lock:
        records = _read_registry()
        records.append(record)
        _write_registry(records)

    return record


# --- deletion ------------------------------------------------------------


def delete_document(document_id: str, user_id: str | None = None) -> int:
    """Remove a paper's vectors, its stored file, and its registry entry."""
    with _registry_lock:
        records = _read_registry()
        target = next((record for record in records if record["id"] == document_id), None)
        if target is None:
            raise DocumentNotFoundError(f"No document with id {document_id}.")
        if user_id and target.get("user_id") and target.get("user_id") != user_id:
            raise DocumentNotFoundError(f"No document with id {document_id} belongs to this account.")

        removed = get_vector_store().delete_document(document_id)

        stored_path = target.get("stored_path")
        if stored_path:
            try:
                Path(stored_path).unlink(missing_ok=True)
            except OSError:
                pass

        _write_registry([record for record in records if record["id"] != document_id])

    return removed
