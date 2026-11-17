"""Step 2 of ingestion: page text -> overlapping chunks with metadata.

Why chunk at all?
  * An embedding vector is a fixed-size summary. Embedding a whole 12-page
    paper produces one blurred vector that is close to everything and useful
    for nothing.
  * Retrieval should return a passage the user can verify, not a whole file.
  * The LLM context window is finite and costly; we want the few hundred words
    that answer the question, not 40,000.

Why overlap?
  A hard cut can land in the middle of the one sentence that matters. Repeating
  the last ~150 characters at the start of the next chunk means a fact that
  straddles a boundary still appears intact in at least one chunk.

Why never merge across pages?
  Every chunk must map to exactly one page so the citation we show the user is
  precise. Keeping chunks inside a page costs a little redundancy and buys
  trustworthy references.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .pdf_loader import PageText

# Tried in order: split on the largest natural boundary that fits.
SEPARATORS = ["\n\n", "\n", ". ", "; ", ", ", " "]


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    text: str
    user_id: str = ""
    metadata: dict = field(default_factory=dict)


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Greedy recursive-style splitter.

    Walks forward taking `chunk_size` characters, then backs up to the nearest
    natural separator so chunks end on sentence/clause boundaries instead of
    mid-word. Each new chunk starts `chunk_overlap` characters early.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)

        if end < length:
            # Only look for a boundary in the last third of the window, so we
            # never produce an absurdly short chunk.
            window_start = start + int(chunk_size * 0.6)
            best = -1
            for separator in SEPARATORS:
                found = text.rfind(separator, window_start, end)
                if found > best:
                    best = found + len(separator)
                if best != -1:
                    break
            if best > start:
                end = best

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= length:
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


def chunk_pages(
    pages: list[PageText],
    document_id: str,
    filename: str,
    chunk_size: int,
    chunk_overlap: int,
    user_id: str = "",
) -> list[Chunk]:
    """Turn extracted pages into chunks, numbering them across the document."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        # PyMuPDF fitz page.number is 0-indexed; ensure 1-indexed page number (page 1 is 1)
        raw_page = getattr(page, "page", 1)
        page_num = max(1, int(raw_page))
        for piece in _split_text(page.text, chunk_size, chunk_overlap):
            chunk_id = f"{document_id}:{index}"
            chunk_metadata = {
                "document_id": document_id,
                "filename": filename,
                "page": page_num,
                "page_number": page_num,
                "chunk_index": index,
                "chunk_id": chunk_id,
                "char_count": len(piece),
                "user_id": user_id,
            }
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    filename=filename,
                    page=page_num,
                    chunk_index=index,
                    text=piece,
                    user_id=user_id,
                    metadata=chunk_metadata,
                )
            )
            index += 1
    return chunks
