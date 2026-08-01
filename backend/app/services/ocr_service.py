"""
OCR + structured field extraction for uploaded documents (§2e).

Provider is swappable via OCR_PROVIDER=tesseract|google_document_ai. Only
`tesseract` (via pytesseract, local/free) is actually implemented — Document
AI needs a real GCP project/processor that doesn't exist for this project
yet, so selecting it currently just falls back to tesseract with a logged
warning rather than raising, same "no-op with a visible log line" pattern
as WhatsAppBusinessAPISender/EmailSender when unconfigured.

Field extraction is deliberately regex/heuristic-based, not ML-based, per
HANDOFF §2e's note not to over-engineer this before there's real document
data to test against.
"""
import io
import logging
import re

from app.core.config import settings

logger = logging.getLogger(__name__)

PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]Z[A-Z\d]\b")
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|\u20b9)\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)


def _run_tesseract(file_bytes: bytes, mime_type: str) -> str:
    import pytesseract
    from PIL import Image

    if mime_type == "application/pdf":
        from pdf2image import convert_from_bytes

        # Explicit DPI ceiling (not pdf2image's default) — this runs on the
        # same small free-tier instance that also serves API requests (see
        # worker/tasks.py's docstring), so keeping per-page memory/CPU
        # bounded matters more here than OCR accuracy at higher resolution.
        # 150 is a reasonable ceiling for OCR purposes, not 300+.
        pages = convert_from_bytes(file_bytes, dpi=settings.OCR_RENDER_DPI)
        return "\n".join(pytesseract.image_to_string(p) for p in pages)

    image = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(image)


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    provider = settings.OCR_PROVIDER
    if provider == "google_document_ai":
        logger.warning(
            "OCR_PROVIDER=google_document_ai is not implemented yet "
            "(no GCP processor configured for this project) — falling "
            "back to tesseract."
        )
    try:
        return _run_tesseract(file_bytes, mime_type)
    except Exception as exc:  # pytesseract/Pillow errors, missing binary, etc.
        logger.error(f"[ocr:extract_text failed] {exc}")
        return ""


def extract_fields(text: str) -> dict:
    """Best-effort regex extraction. Returns whatever it finds; missing
    keys just aren't included rather than set to null."""
    fields: dict = {}
    if pan := PAN_RE.search(text):
        fields["pan"] = pan.group(0)
    if gstin := GSTIN_RE.search(text):
        fields["gstin"] = gstin.group(0)
    if dates := DATE_RE.findall(text):
        fields["dates"] = list(dict.fromkeys(dates))[:5]
    if amounts := AMOUNT_RE.findall(text):
        fields["amounts"] = list(dict.fromkeys(amounts))[:5]
    return fields


def confidence_for(text: str, fields: dict) -> float:
    """Crude heuristic, not a real OCR confidence score (tesseract's own
    per-word confidence isn't threaded through image_to_string): more
    recognized text and more matched fields -> higher confidence."""
    if not text.strip():
        return 0.0
    score = min(len(text) / 500, 0.6) + min(len(fields) * 0.1, 0.4)
    return round(min(score, 1.0), 2)
