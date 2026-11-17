"""The RAG pipeline itself: the two flows everything else calls into.

Ingestion
    PDF bytes -> extract pages -> clean -> chunk (+ metadata)
              -> embed -> store in Chroma

Query
    question -> embed -> similarity search (top-K, optional doc filter)
             -> relevance cut-off -> numbered context -> prompt -> Gemini
             -> answer + resolved source references

The full text of a PDF is never sent to the model. Only the retrieved chunks
are, which is the whole point of retrieval augmentation.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass

from ..config import settings
from ..errors import LLMError, MissingAPIKeyError
from .chunker import chunk_pages
from .embeddings import get_embedder
from .pdf_loader import extract_pages
from .prompts import NO_CONTEXT_ANSWER, build_context, build_prompt
from .vector_store import RetrievedChunk, get_vector_store

EXCERPT_CHARS = 320
_llm_lock = threading.Lock()
_llm_ready = False


# --- ingestion -----------------------------------------------------------


@dataclass
class IngestResult:
    document_id: str
    pages: int
    chunks: int


def ingest_pdf(pdf_bytes: bytes, filename: str, document_id: str, user_id: str = "") -> IngestResult:
    """Run a PDF through the full ingestion half of the pipeline."""
    pages = extract_pages(pdf_bytes, filename)

    chunks = chunk_pages(
        pages=pages,
        document_id=document_id,
        filename=filename,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        user_id=user_id,
    )
    if not chunks:
        from ..errors import NoExtractableTextError

        raise NoExtractableTextError(f"{filename} produced no usable text chunks.")

    embeddings = get_embedder().embed_documents([chunk.text for chunk in chunks])
    get_vector_store().add_chunks(chunks, embeddings)

    return IngestResult(
        document_id=document_id,
        pages=len({page.page for page in pages}),
        chunks=len(chunks),
    )


# --- LLM -----------------------------------------------------------------


def _configure_genai():
    global _llm_ready
    import google.generativeai as genai

    if not settings.google_api_key:
        raise MissingAPIKeyError(
            "GOOGLE_API_KEY is not set, so answers cannot be generated. "
            "Add your key to backend/.env and restart the server."
        )
    if not _llm_ready:
        with _llm_lock:
            if not _llm_ready:
                try:
                    genai.configure(api_key=settings.google_api_key, transport="rest")
                except Exception:
                    genai.configure(api_key=settings.google_api_key)
                _llm_ready = True
    return genai


def _generate(prompt: str) -> str:
    genai = _configure_genai()

    models_to_try = [
        settings.gemini_model,
        "models/gemini-flash-latest",
        "models/gemini-3.8-flash",
        "models/gemini-2.5-flash-lite",
        "gemini-2.0-flash",
    ]
    seen = set()
    candidate_models = []
    for m in models_to_try:
        if m and m not in seen:
            seen.add(m)
            candidate_models.append(m)

    last_error: Exception | None = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={
                    # Low temperature: we want faithful reading, not creativity.
                    "temperature": 0.2,
                    "max_output_tokens": 2048,
                },
            )
            text = (getattr(response, "text", "") or "").strip()
            if text:
                return text
        except Exception as exc:
            last_error = exc
            err_msg = str(exc).lower()
            if "not found" in err_msg or "not supported" in err_msg or "no longer available" in err_msg:
                continue
            # If rate limit or other temporary failure on this model, try next model
            continue

    if last_error:
        message = str(last_error)
        if "quota" in message.lower() or "429" in message:
            raise LLMError(
                "The model API hit its rate limit. Wait a moment and ask again.",
                detail=message[:200],
            ) from last_error
        if "api key" in message.lower() or "permission" in message.lower():
            raise LLMError(
                "The model API rejected the credentials. Check GOOGLE_API_KEY in backend/.env.",
                detail=message[:200],
            ) from last_error
        raise LLMError(
            "The model API call failed. Check your network connection and try again.",
            detail=message[:200],
        ) from last_error

    raise LLMError(
        "The model returned an empty response, usually because the request was filtered. "
        "Try rephrasing the question."
    )


# --- query ---------------------------------------------------------------


@dataclass
class Source:
    label: str
    chunk: RetrievedChunk


@dataclass
class AnswerResult:
    answer: str
    mode: str
    sources: list[Source]
    grounded: bool


def _excerpt(text: str) -> str:
    condensed = " ".join(text.split())
    if len(condensed) <= EXCERPT_CHARS:
        return condensed
    return condensed[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "..."


def _cited_labels(answer: str) -> set[str]:
    labels = set()
    # Matches bracket contents and extracts any S<digits> tokens (case-insensitive)
    for bracket_content in re.findall(r"\[([^\]]+)\]", answer):
        for token in re.findall(r"\b[Ss](\d+)\b", bracket_content):
            labels.add(f"S{token}")
    return labels


def _cosine_similarity(v1, v2) -> float:
    if v1 is None or v2 is None:
        return 0.0
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(v1, v2):
        a_f = float(a)
        b_f = float(b)
        dot += a_f * b_f
        norm1 += a_f * a_f
        norm2 += b_f * b_f
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    return dot / ((norm1 ** 0.5) * (norm2 ** 0.5))


def _text_overlap_ratio(text_a: str, text_b: str) -> float:
    """Calculate token-level overlap (containment and Jaccard) between two chunk texts."""
    words_a = set(re.findall(r"\w+", text_a.lower()))
    words_b = set(re.findall(r"\w+", text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    common = words_a.intersection(words_b)
    jaccard = len(common) / len(words_a.union(words_b))
    containment = max(len(common) / len(words_a), len(common) / len(words_b))
    return max(jaccard, containment)


def _is_redundant_chunk(candidate: RetrievedChunk, selected: list[RetrievedChunk]) -> bool:
    """Check if candidate chunk is redundant with any already selected chunk."""
    cand_text = candidate.text.strip().lower()

    for s in selected:
        sel_text = s.text.strip().lower()

        # Exact match
        if cand_text == sel_text:
            return True

        # Check overall text overlap (>85% text overlap anywhere)
        overlap = _text_overlap_ratio(cand_text, sel_text)
        if overlap >= 0.85:
            return True

        # Same document and same page:
        # Prevent multiple chunks pointing to the exact same page with identical/near-identical scores
        # (e.g., S2 and S4 both pointing to page 3 with 65% match).
        if candidate.document_id == s.document_id and candidate.page == s.page:
            if overlap >= 0.30 or abs(candidate.score - s.score) <= 0.05:
                return True
            # Restrict to at most 1 chunk per page from the same document
            return True

    return False


def mmr_rerank_and_deduplicate(
    candidates: list[RetrievedChunk],
    top_k: int,
    lambda_param: float = 0.7,
) -> list[RetrievedChunk]:
    """Maximal Marginal Relevance (MMR) reranking combined with same-page & text deduplication.

    Balances query relevance against redundancy with already selected chunks.
    """
    if not candidates:
        return []

    selected: list[RetrievedChunk] = []
    remaining = list(candidates)

    while remaining and len(selected) < top_k:
        best_candidate: RetrievedChunk | None = None
        best_score = float("-inf")

        for cand in remaining:
            if _is_redundant_chunk(cand, selected):
                continue

            relevance = max(0.0, 1.0 - cand.distance)
            if not selected or cand.embedding is None or len(cand.embedding) == 0:
                mmr_score = relevance
            else:
                max_sim = max(
                    (
                        _cosine_similarity(cand.embedding, s.embedding)
                        for s in selected
                        if s.embedding is not None and len(s.embedding) > 0
                    ),
                    default=0.0,
                )
                mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_candidate = cand

        if best_candidate is None:
            break

        selected.append(best_candidate)
        remaining.remove(best_candidate)

    return selected


def deduplicate_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Filter out overlapping or near-duplicate chunks, keeping the highest-ranked ones."""
    return mmr_rerank_and_deduplicate(chunks, top_k=len(chunks))


def answer_question(
    question: str,
    mode: str = "simple",
    document_ids: list[str] | None = None,
    history: list[tuple[str, str]] | None = None,
    user_id: str | None = None,
) -> AnswerResult:
    """Run the query half of the pipeline and return a grounded answer."""
    query_vector = get_embedder().embed_query(question)

    # Fetch 3x top_k candidate pool for MMR reranking and deduplication
    retrieved = get_vector_store().search(
        query_embedding=query_vector,
        top_k=settings.top_k * 3,
        document_ids=document_ids,
        include_embeddings=True,
        user_id=user_id,
    )

    # Drop anything the index considers only loosely related
    relevant_candidates = [chunk for chunk in retrieved if chunk.distance <= settings.max_distance]

    # Apply MMR reranking and filter out duplicate/overlapping same-page chunks
    relevant = mmr_rerank_and_deduplicate(
        candidates=relevant_candidates,
        top_k=settings.top_k,
        lambda_param=0.7,
    )

    if not relevant:
        return AnswerResult(answer=NO_CONTEXT_ANSWER, mode=mode, sources=[], grounded=False)

    context, label_map = build_context(relevant)
    prompt = build_prompt(question=question, context=context, mode=mode, history=history)
    answer = _generate(prompt)

    # Show the passages the model actually cited; if it cited none, show all
    # retrieved passages so the user can still check the reasoning.
    cited = _cited_labels(answer)
    labels = [label for label in label_map if label in cited] or list(label_map.keys())
    sources = [Source(label=label, chunk=label_map[label]) for label in labels]

    return AnswerResult(answer=answer, mode=mode, sources=sources, grounded=bool(cited))


def source_excerpt(chunk: RetrievedChunk) -> str:
    return _excerpt(chunk.text)


def reset_llm() -> None:
    global _llm_ready
    with _llm_lock:
        _llm_ready = False


def llm_configured() -> bool:
    return bool(settings.google_api_key)
