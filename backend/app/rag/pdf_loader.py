"""Step 1 of ingestion: PDF -> clean text, one entry per page.

Page numbers are captured here and carried all the way through chunking and
retrieval, which is what makes "see page 7 of smith2023.pdf" possible later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pymupdf as fitz

from ..errors import NoExtractableTextError, PDFExtractionError

# A page with almost no text is usually a figure page or a scan.
MIN_CHARS_PER_PAGE = 30
# If the whole document has less than this, extraction effectively failed.
MIN_CHARS_PER_DOC = 200


@dataclass
class PageText:
    page: int  # 1-based, as a human would cite it
    text: str


def clean_text(raw: str) -> str:
    """Normalise the messy text that comes out of academic PDFs.

    Removes hyphenation across line breaks, collapses the single newlines that
    two-column layouts sprinkle mid-sentence, and trims repeated whitespace --
    all of which otherwise pollute chunks and hurt embedding quality.
    """
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    # Drop control characters and the ligature/box glyphs PDFs love.
    text = text.replace("\u00ad", "").replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    # "hyphen-\nated" -> "hyphenated"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # A single newline inside a sentence is a layout artefact; a blank line is
    # a real paragraph break and is kept.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_ocr_from_page(page_obj) -> str:
    """Fallback OCR: renders page to image and extracts text via pytesseract or Gemini Vision."""
    try:
        pix = page_obj.get_pixmap(dpi=150)
        png_bytes = pix.tobytes("png")
    except Exception:
        return ""

    # 1. Try local pytesseract if available
    try:
        import io
        from PIL import Image
        import pytesseract

        img = Image.open(io.BytesIO(png_bytes))
        tess_text = pytesseract.image_to_string(img)
        if len(tess_text.strip()) >= MIN_CHARS_PER_PAGE:
            return tess_text
    except Exception:
        pass

    # 2. Fallback to Gemini Multimodal Vision extraction
    from ..config import settings

    if settings.google_api_key:
        try:
            import google.generativeai as genai

            try:
                genai.configure(api_key=settings.google_api_key, transport="rest")
            except Exception:
                genai.configure(api_key=settings.google_api_key)

            models_to_try = [
                settings.gemini_model,
                "models/gemini-flash-latest",
                "models/gemini-3.8-flash",
                "models/gemini-2.5-flash-image",
            ]
            for model_name in models_to_try:
                try:
                    vision_model = genai.GenerativeModel(model_name)
                    res = vision_model.generate_content(
                        [
                            {"mime_type": "image/png", "data": png_bytes},
                            "Extract all readable text, labels, diagram content, code, and tables from this document page verbatim. Do not summarize or add commentary.",
                        ],
                        generation_config={"temperature": 0.1, "max_output_tokens": 1500},
                        request_options={"timeout": 35},
                    )
                    v_text = (getattr(res, "text", "") or "").strip()
                    if len(v_text) >= MIN_CHARS_PER_PAGE:
                        return v_text
                except Exception:
                    continue
        except Exception:
            pass

    return ""


def extract_pages(pdf_bytes: bytes, filename: str) -> list[PageText]:
    """Return cleaned text for every page that actually has text (with OCR fallback for screenshots)."""
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # corrupt header, encrypted, truncated upload
        raise PDFExtractionError(
            f"{filename} could not be opened as a PDF.",
            detail=str(exc)[:200],
        ) from exc

    try:
        if document.needs_pass:
            raise PDFExtractionError(
                f"{filename} is password protected. Remove the password and upload it again."
            )
        if document.page_count == 0:
            raise PDFExtractionError(f"{filename} has no pages.")

        pages: list[PageText] = []
        total_chars = 0
        for index in range(document.page_count):
            try:
                page_obj = document.load_page(index)
                raw = page_obj.get_text("text")
            except Exception:
                # One unreadable page should not sink the whole paper.
                continue

            cleaned = clean_text(raw)

            # If page contains embedded screenshots, diagrams, or scans with little/no text, run fallback OCR
            if len(cleaned) < MIN_CHARS_PER_PAGE:
                ocr_text = _extract_ocr_from_page(page_obj)
                if ocr_text:
                    cleaned = clean_text(ocr_text)

            total_chars += len(cleaned)
            if len(cleaned) >= MIN_CHARS_PER_PAGE:
                # PyMuPDF fitz page.number is 0-indexed (page 0 is page 1); store 1-indexed page_number = page.number + 1
                page_number = int(getattr(page_obj, "number", index)) + 1
                pages.append(PageText(page=page_number, text=cleaned))
    finally:
        document.close()

    if total_chars < MIN_CHARS_PER_DOC or not pages:
        raise NoExtractableTextError(
            f"No readable text found in {filename}. Scanned or image-only PDFs need OCR first.",
        )

    return pages
