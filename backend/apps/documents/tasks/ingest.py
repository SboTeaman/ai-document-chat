import logging
from datetime import UTC, datetime

from celery import shared_task
from django.conf import settings
from django.db import transaction

from apps.documents.models import Document, DocumentChunk

from .chunking import Chunk, chunk_text
from .embedding import generate_embeddings
from .extraction import ExtractionError, extract_text

# Failures that should not be retried — they are deterministic given the input.
NON_RETRYABLE_EXC = (ExtractionError, ValueError)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    name="documents.ingest_document",
)
def ingest_document(self, document_id: int) -> dict:
    """Run the full ingestion pipeline for one document.

    Download → extract text → chunk → embed → save chunks, flipping the
    document's status to READY on success. Deterministic input errors fail
    immediately; transient errors are retried with exponential backoff and the
    document is marked FAILED once the retry budget is exhausted.
    """
    logger.info("Starting ingestion", extra={"document_id": document_id, "attempt": self.request.retries + 1})

    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error("Document not found", extra={"document_id": document_id})
        return {"status": "error", "reason": "document_not_found"}

    _update_status(document, Document.Status.PROCESSING)

    try:
        file_bytes = _download_file(document.s3_key)
        text = extract_text(file_bytes, document.mime_type)

        if not text.strip():
            raise ValueError("Document contains no extractable text.")

        chunks = chunk_text(
            text,
            chunk_size=settings.CHUNK_SIZE_TOKENS,
            overlap=settings.CHUNK_OVERLAP_TOKENS,
        )

        if not chunks:
            raise ValueError("Chunking produced no output.")

        max_chunks = settings.MAX_CHUNKS_PER_DOCUMENT
        if len(chunks) > max_chunks:
            raise ValueError(f"Document produced {len(chunks)} chunks; max allowed is {max_chunks}.")

        texts = [c.content for c in chunks]
        # Namespace the checkpoint by document so a retried ingest resumes from
        # the last embedded chunk instead of re-embedding everything.
        embeddings = generate_embeddings(texts, cache_namespace=f"doc:{document.id}")

        _save_chunks(document, chunks, embeddings)

        document.status = Document.Status.READY
        document.chunk_count = len(chunks)
        document.processing_finished_at = datetime.now(UTC)
        document.error_message = ""
        document.save(update_fields=["status", "chunk_count", "processing_finished_at", "error_message"])

        logger.info(
            "Ingestion complete",
            extra={"document_id": document_id, "chunks": len(chunks)},
        )
        return {"status": "ok", "chunks": len(chunks)}

    except NON_RETRYABLE_EXC as exc:
        # Deterministic input errors — fail immediately instead of burning retries.
        _mark_failed(document, exc)
        logger.error(
            "Ingestion rejected (non-retryable)",
            extra={"document_id": document_id, "error": str(exc)},
        )
        return {"status": "failed", "reason": str(exc)}

    except Exception as exc:
        logger.warning(
            "Ingestion failed",
            extra={
                "document_id": document_id,
                "error": str(exc),
                "attempt": self.request.retries + 1,
            },
        )
        # celery's retry(exc=...) re-raises the *original* exception once the
        # retry budget is exhausted (not MaxRetriesExceededError), so check the
        # budget ourselves and mark the document failed when it runs out.
        if self.request.retries >= self.max_retries:
            _mark_failed(document, exc)
            logger.error(
                "Ingestion permanently failed",
                extra={"document_id": document_id, "error": str(exc)},
            )
            return {"status": "failed", "reason": str(exc)}
        # celery's retry() raises a Retry internally; `from exc` never applies, so
        # the B904 chaining rule does not fit here.
        raise self.retry(exc=exc, countdown=30 * (2**self.request.retries))  # noqa: B904


def _mark_failed(document: Document, exc: Exception) -> None:
    """Flip the document to FAILED and record a truncated error message."""
    document.status = Document.Status.FAILED
    document.error_message = str(exc)[:1000]
    document.processing_finished_at = datetime.now(UTC)
    document.save(update_fields=["status", "error_message", "processing_finished_at"])


def _download_file(s3_key: str) -> bytes:
    """Fetch the raw file bytes from object storage (indirection eases mocking)."""
    from common.storage import download_file_bytes

    return download_file_bytes(s3_key)


def _update_status(document: Document, status: Document.Status) -> None:
    """Persist a status change, stamping processing_started_at when relevant."""
    update_fields = ["status"]
    document.status = status
    if status == Document.Status.PROCESSING:
        document.processing_started_at = datetime.now(UTC)
        update_fields.append("processing_started_at")
    document.save(update_fields=update_fields)


def _save_chunks(document: Document, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    """Atomically replace the document's chunks with the freshly embedded set."""
    if len(chunks) != len(embeddings):
        raise ValueError(f"Chunk/embedding count mismatch: {len(chunks)} chunks, {len(embeddings)} embeddings")

    with transaction.atomic():
        DocumentChunk.objects.filter(document=document).delete()

        chunk_objects = [
            DocumentChunk(
                document=document,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings, strict=False)
        ]
        DocumentChunk.objects.bulk_create(chunk_objects, batch_size=200)
