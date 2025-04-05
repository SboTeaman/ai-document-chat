import io
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.documents import services
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer
from tests.factories import CollectionFactory, DocumentFactory, WorkspaceFactory


def _file(content: bytes, name="doc.txt"):
    f = io.BytesIO(content)
    f.name = name
    return f


@pytest.mark.django_db
class TestUploadDocument:
    def test_happy_path_creates_document_and_queues_ingest(self):
        ws = WorkspaceFactory()
        with (
            patch("apps.documents.services.upload_file", return_value="key") as up,
            patch("apps.documents.services.ingest_document.apply_async") as ingest,
        ):
            doc = services.upload_document(
                file_obj=_file(b"hello world plain text"),
                workspace_id=ws.id,
                collection_id=None,
                uploaded_by=ws.owner,
            )
        assert doc.status == Document.Status.QUEUED
        up.assert_called_once()
        ingest.assert_called_once()


@pytest.mark.django_db
class TestValidateFile:
    def test_too_large(self):
        with pytest.raises(ValidationError, match="too large"):
            services._validate_file(b"x" * 10, "f.txt", 50 * 1024 * 1024)

    def test_empty(self):
        with pytest.raises(ValidationError, match="empty"):
            services._validate_file(b"", "f.txt", 0)

    def test_unsupported_type(self):
        with pytest.raises(ValidationError, match="Unsupported"):
            services._validate_file(b"\x7fELF\x02\x01\x01\x00 binary", "f.bin", 12)

    def test_accepts_plain_text(self):
        assert services._validate_file(b"hello text content", "f.txt", 18) == "text/plain"


@pytest.mark.django_db
class TestQuota:
    @override_settings(WORKSPACE_STORAGE_QUOTA_MB=0)
    def test_quota_exceeded(self):
        ws = WorkspaceFactory()
        DocumentFactory(workspace=ws, file_size_bytes=1024)
        with pytest.raises(ValidationError, match="quota exceeded"):
            services._check_workspace_quota(ws.id, 1)


@pytest.mark.django_db
class TestDeleteDocument:
    def test_deletes_row_and_file(self):
        doc = DocumentFactory()
        with patch("apps.documents.services.delete_file") as df:
            services.delete_document(doc)
        df.assert_called_once()
        assert not Document.objects.filter(id=doc.id).exists()

    def test_s3_error_is_non_fatal(self):
        doc = DocumentFactory()
        with patch("apps.documents.services.delete_file", side_effect=Exception("boom")):
            services.delete_document(doc)
        assert not Document.objects.filter(id=doc.id).exists()


@pytest.mark.django_db
class TestDocumentSerializer:
    def test_handles_null_collection_and_uploader(self):
        doc = DocumentFactory(collection=None, uploaded_by=None)
        data = DocumentSerializer(doc).data
        assert data["collection"] is None
        assert data["uploaded_by"] is None
        assert data["file_size_kb"] == round(doc.file_size_bytes / 1024, 1)

    def test_serialises_collection_and_uploader(self):
        col = CollectionFactory()
        doc = DocumentFactory(collection=col, workspace=col.workspace)
        data = DocumentSerializer(doc).data
        assert data["collection"]["id"] == col.id
        assert data["uploaded_by"]["email"] == doc.uploaded_by.email


@pytest.mark.django_db
class TestUploadSerializerCollectionValidation:
    def test_none_collection_ok(self):
        ws = WorkspaceFactory()
        s = DocumentUploadSerializer(workspace_id=ws.id)
        assert s.validate_collection_id(None) is None

    def test_missing_workspace_context(self):
        s = DocumentUploadSerializer()
        with pytest.raises(ValidationError, match="Workspace context"):
            s.validate_collection_id(1)

    def test_collection_in_other_workspace_rejected(self):
        ws = WorkspaceFactory()
        other_col = CollectionFactory()
        s = DocumentUploadSerializer(workspace_id=ws.id)
        with pytest.raises(ValidationError, match="not found"):
            s.validate_collection_id(other_col.id)

    def test_valid_collection_accepted(self):
        col = CollectionFactory()
        s = DocumentUploadSerializer(workspace_id=col.workspace_id)
        assert s.validate_collection_id(col.id) == col.id
