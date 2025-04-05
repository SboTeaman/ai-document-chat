import io
import logging
import zipfile

logger = logging.getLogger(__name__)

# Hard caps that protect the Celery worker from resource-exhaustion attacks
# (e.g. multi-thousand-page PDFs or DOCX/ZIP bombs that decompress to GBs).
MAX_PDF_PAGES = 1000
MAX_DOCX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB
MAX_EXTRACTED_TEXT_CHARS = 20 * 1024 * 1024  # 20 MB of UTF-8 text


class ExtractionError(ValueError):
    """Raised when extraction is refused for safety reasons."""


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    """Dispatch to the right extractor by MIME type and enforce the size cap.

    Raises ``ExtractionError`` for unsupported types or oversized output.
    """
    extractors = {
        "application/pdf": _extract_pdf,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": _extract_docx,
        "text/plain": _extract_plain,
        "text/markdown": _extract_plain,
    }
    extractor = extractors.get(mime_type)
    if extractor is None:
        raise ExtractionError(f"Unsupported MIME type: {mime_type}")
    text = extractor(file_bytes)
    if len(text) > MAX_EXTRACTED_TEXT_CHARS:
        raise ExtractionError("Extracted text exceeds the maximum allowed size.")
    logger.debug("Text extracted", extra={"mime_type": mime_type, "chars": len(text)})
    return text


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF, refusing files over the page-count cap."""
    import pdfplumber

    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        if len(pdf.pages) > MAX_PDF_PAGES:
            raise ExtractionError(f"PDF has {len(pdf.pages)} pages; max allowed is {MAX_PDF_PAGES}.")
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    """Extract paragraph text from a DOCX after a zip-bomb safety check."""
    _guard_docx_bomb(file_bytes)

    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _guard_docx_bomb(file_bytes: bytes) -> None:
    """Reject DOCX archives that would expand beyond MAX_DOCX_UNCOMPRESSED_BYTES.

    DOCX is a ZIP container; without this check a 1 MB upload could decompress
    to several GBs inside python-docx and exhaust the worker's memory.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            total = sum(info.file_size for info in zf.infolist())
    except zipfile.BadZipFile as exc:
        raise ExtractionError("DOCX file is not a valid archive.") from exc
    if total > MAX_DOCX_UNCOMPRESSED_BYTES:
        raise ExtractionError(f"DOCX uncompressed size {total} exceeds limit of {MAX_DOCX_UNCOMPRESSED_BYTES} bytes.")


def _extract_plain(file_bytes: bytes) -> str:
    """Decode plain-text / Markdown bytes as UTF-8, replacing bad bytes."""
    return file_bytes.decode("utf-8", errors="replace")
