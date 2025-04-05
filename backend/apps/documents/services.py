import logging

import magic
from django.conf import settings
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from common.storage import delete_file, upload_file

from .models import Document
from .tasks.ingest import ingest_document

logger = logging.getLogger(__name__)


def upload_document(*, file_obj, workspace_id: int, collection_id: int | None, uploaded_by) -> Document:
    """Validate + store an uploaded file and queue async ingestion.

    Returns the created ``Document`` in QUEUED status; raises ``ValidationError``
    on bad type/size or when the workspace storage quota would be exceeded.
    """
    file_bytes = file_obj.read()
    file_obj.seek(0)

    mime_type = _validate_file(file_bytes, file_obj.name, len(file_bytes))
    _check_workspace_quota(workspace_id, len(file_bytes))

    s3_key = upload_file(file_obj, workspace_id, file_obj.name)

    document = Document.objects.create(
        workspace_id=workspace_id,
        collection_id=collection_id,
        uploaded_by=uploaded_by,
        filename=file_obj.name,
        s3_key=s3_key,
        mime_type=mime_type,
        file_size_bytes=len(file_bytes),
        status=Document.Status.QUEUED,
    )

    ingest_document.apply_async(args=[document.id], countdown=1)
    logger.info("Document queued", extra={"document_id": document.id, "workspace_id": workspace_id})
    return document


def delete_document(document: Document) -> None:
    """Delete the document row and its stored file (S3 failures are non-fatal)."""
    try:
        delete_file(document.s3_key)
    except Exception as exc:
        # S3 errors are non-fatal: the row still gets removed, but we want a trail.
        logger.warning("S3 delete failed", extra={"s3_key": document.s3_key, "error": str(exc)})
    document.delete()


def _validate_file(file_bytes: bytes, filename: str, size: int) -> str:
    """Enforce size limits and sniff the real MIME type via magic bytes.

    Returns the detected MIME type; raises ``ValidationError`` if the file is
    empty, too large, or of a disallowed type.
    """
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size > max_size:
        raise ValidationError(f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB} MB.")

    if size == 0:
        raise ValidationError("File is empty.")

    mime_type = magic.from_buffer(file_bytes, mime=True)
    if mime_type not in settings.ALLOWED_MIME_TYPES:
        raise ValidationError(f"Unsupported file type: {mime_type}. Allowed: PDF, DOCX, TXT, MD.")
    return mime_type


def _check_workspace_quota(workspace_id: int, incoming_size: int) -> None:
    """Raise ``ValidationError`` if adding ``incoming_size`` would exceed the quota."""
    quota_bytes = settings.WORKSPACE_STORAGE_QUOTA_MB * 1024 * 1024
    used = Document.objects.filter(workspace_id=workspace_id).aggregate(total=Sum("file_size_bytes"))["total"] or 0
    if used + incoming_size > quota_bytes:
        remaining_mb = max(0, (quota_bytes - used) // (1024 * 1024))
        raise ValidationError(
            f"Workspace storage quota exceeded. Remaining: {remaining_mb} MB of {settings.WORKSPACE_STORAGE_QUOTA_MB} MB."
        )
