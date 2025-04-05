from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.authentication.models import AuditLog
from apps.documents.models import Document
from apps.workspaces.models import WorkspaceMember
from tests.factories import (
    CollectionFactory,
    DocumentFactory,
    UserFactory,
    WorkspaceMemberFactory,
)


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.mark.django_db
class TestDocumentList:
    def test_list_with_filters(self):
        m = WorkspaceMemberFactory()
        col = CollectionFactory(workspace=m.workspace)
        DocumentFactory(workspace=m.workspace, collection=col, status=Document.Status.READY)
        DocumentFactory(workspace=m.workspace, status=Document.Status.FAILED)
        base = f"/api/workspaces/{m.workspace_id}/documents/"
        assert len(client_for(m.user).get(base).json()["data"]) == 2
        assert len(client_for(m.user).get(base, {"collection_id": col.id}).json()["data"]) == 1
        assert len(client_for(m.user).get(base, {"status": "failed"}).json()["data"]) == 1


@pytest.mark.django_db
class TestDocumentUpload:
    def test_member_uploads_and_it_is_audited(self):
        m = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        file = SimpleUploadedFile("doc.txt", b"hello world this is a text document", content_type="text/plain")
        with (
            patch("apps.documents.services.upload_file", return_value="workspaces/1/x/doc.txt"),
            patch("apps.documents.services.ingest_document.apply_async"),
        ):
            r = client_for(m.user).post(
                f"/api/workspaces/{m.workspace_id}/documents/", {"file": file}, format="multipart"
            )
        assert r.status_code == 202
        assert Document.objects.filter(workspace=m.workspace).count() == 1
        assert AuditLog.objects.filter(action="document.upload").exists()

    def test_viewer_cannot_upload(self):
        viewer = WorkspaceMemberFactory(role=WorkspaceMember.Role.VIEWER)
        file = SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain")
        r = client_for(viewer.user).post(
            f"/api/workspaces/{viewer.workspace_id}/documents/", {"file": file}, format="multipart"
        )
        assert r.status_code == 403


@pytest.mark.django_db
class TestDocumentDetail:
    def test_get_detail(self):
        m = WorkspaceMemberFactory()
        doc = DocumentFactory(workspace=m.workspace)
        r = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/documents/{doc.id}/")
        assert r.status_code == 200
        assert r.json()["data"]["filename"] == doc.filename

    def test_get_missing_404(self):
        m = WorkspaceMemberFactory()
        r = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/documents/999999/")
        assert r.status_code == 404

    def test_download_returns_presigned_url(self):
        m = WorkspaceMemberFactory()
        doc = DocumentFactory(workspace=m.workspace)
        with patch("apps.documents.views.get_presigned_url", return_value="https://signed"):
            r = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/documents/{doc.id}/download/")
        assert r.status_code == 200
        assert r.json()["data"]["url"] == "https://signed"

    def test_download_missing_404(self):
        m = WorkspaceMemberFactory()
        r = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/documents/999999/download/")
        assert r.status_code == 404

    def test_uploader_can_delete_own(self):
        m = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        doc = DocumentFactory(workspace=m.workspace, uploaded_by=m.user)
        with patch("apps.documents.services.delete_file"):
            r = client_for(m.user).delete(f"/api/workspaces/{m.workspace_id}/documents/{doc.id}/")
        assert r.status_code == 204
        assert not Document.objects.filter(id=doc.id).exists()
        assert AuditLog.objects.filter(action="document.delete").exists()

    def test_member_cannot_delete_others_document(self):
        m = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        doc = DocumentFactory(workspace=m.workspace, uploaded_by=UserFactory())
        r = client_for(m.user).delete(f"/api/workspaces/{m.workspace_id}/documents/{doc.id}/")
        assert r.status_code == 403
