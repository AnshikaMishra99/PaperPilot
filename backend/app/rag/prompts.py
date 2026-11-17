"""Prompt construction -- the "G" in RAG.

Retrieval decides *what* the model sees; the prompt decides *how* it is allowed
to use it. The rules below push the model to answer only from the supplied
passages, to admit when the passages do not contain the answer, and to cite the
numbered sources so a reader can check any claim.

Grounding like this reduces unsupported answers. It does not eliminate them:
the model can still misread a passage, and retrieval can still miss the right
one. The UI shows sources precisely so the user can verify.
"""

from __future__ import annotations

from .vector_store import RetrievedChunk

BASE_RULES = """You are PaperPilot, an assistant that answers questions about research papers.

Rules you must follow:
1. Answer using ONLY the numbered source passages provided below. Do not use outside knowledge, and do not guess.
2. STRICT CITATION RULE: You MUST cite every factual statement using the exact source ID tags provided in the context (e.g., [S1], [S2]) immediately after the relevant sentence or clause. Never state a fact without attaching its citation marker.
3. 1-Shot Citation Example:
   "Supervised learning algorithms require labeled training datasets to train predictive models [S1], whereas unsupervised learning clusters unlabeled observations to discover hidden structures [S2]. Convolutional layers extract hierarchical spatial features from input images [S1][S3]."
4. If the passages do not contain enough information to answer, say so plainly and name what is missing. Do not invent a plausible-sounding answer.
5. If the question asks about several papers, make clear which paper each point comes from by naming the file.
6. Never claim a passage says something it does not say. Quote sparingly and briefly when exact wording matters.
7. If the passages only partially answer the question, give the part you can support and state what is not covered.
8. Complete your response fully and coherently; never end an answer mid-sentence."""

SIMPLE_STYLE = """Style for this answer:
Write for a reader who is new to the field. Use everyday language, expand any acronym the first time it appears, and explain technical terms clearly. Prefer short paragraphs and concrete explanations. Ensure your explanation is complete, thorough, and answers the question completely without trailing off."""

TECHNICAL_STYLE = """Style for this answer:
Write for a reader who works in the field. Use the paper's own terminology, keep the precise names of methods, datasets, metrics and baselines, and report numbers exactly as the passages give them. Note assumptions, ablations and stated limitations where the passages mention them. Be dense and comprehensive, completing all points thoroughly."""

NO_CONTEXT_ANSWER = (
    "I could not find anything relevant to that question in the uploaded papers. "
    "Try rephrasing it, using wording closer to the paper's own terms, or upload the paper "
    "that covers this topic."
)


def build_context(chunks: list[RetrievedChunk]) -> tuple[str, dict[str, RetrievedChunk]]:
    """Render retrieved chunks as a numbered, labelled context block.

    Returns the text block and a label -> chunk map so the API response can
    describe exactly which passage each label refers to.
    """
    blocks: list[str] = []
    label_map: dict[str, RetrievedChunk] = {}

    for position, chunk in enumerate(chunks, start=1):
        label = f"S{position}"
        label_map[label] = chunk
        blocks.append(
            f"[{label}] Paper: {chunk.filename} | Page: {chunk.page}\n{chunk.text}"
        )

    return "\n\n---\n\n".join(blocks), label_map


def build_history_block(history: list[tuple[str, str]]) -> str:
    """Compact transcript of recent turns, for resolving follow-up questions."""
    if not history:
        return ""
    lines = [
        f"{'User' if role == 'user' else 'PaperPilot'}: {content.strip()[:500]}"
        for role, content in history
    ]
    return (
        "Earlier in this conversation (for resolving references like "
        '"it" or "that method" only -- never as a source of facts):\n'
        + "\n".join(lines)
    )


def build_prompt(
    question: str,
    context: str,
    mode: str,
    history: list[tuple[str, str]] | None = None,
) -> str:
    style = TECHNICAL_STYLE if mode == "technical" else SIMPLE_STYLE
    history_block = build_history_block(history or [])

    sections = [BASE_RULES, style]
    if history_block:
        sections.append(history_block)
    sections.append(f"Source passages:\n\n{context}")
    sections.append(f"Question: {question.strip()}\n\nAnswer:")

    return "\n\n".join(sections)
