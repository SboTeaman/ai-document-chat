from unittest.mock import patch

import pytest

from apps.documents.models import Document
from apps.workspaces.models import WorkspaceMember
from tests.factories import DocumentChunkFactory, DocumentFactory, UserFactory, WorkspaceFactory, WorkspaceMemberFactory

MOCK_EMBEDDING = [0.1] * 768


@pytest.mark.django_db
class TestHybridSearch:
    def setup_method(self):
        self.user = UserFactory()
        self.workspace = WorkspaceFactory(owner=self.user)
        WorkspaceMemberFactory(workspace=self.workspace, user=self.user, role=WorkspaceMember.Role.OWNER)

        self.document = DocumentFactory(workspace=self.workspace, status=Document.Status.READY)
        self.chunk = DocumentChunkFactory(
            document=self.document,
            content="Python is a great programming language for backend development.",
            embedding=MOCK_EMBEDDING,
        )

    def test_search_returns_results(self):
        from apps.search.services import hybrid_search

        with patch("apps.search.services.generate_query_embedding", return_value=MOCK_EMBEDDING):
            results = hybrid_search("Python programming", self.workspace.id, limit=5)

        assert len(results) >= 1

    def test_search_result_fields(self):
        from apps.search.services import hybrid_search

        with patch("apps.search.services.generate_query_embedding", return_value=MOCK_EMBEDDING):
            results = hybrid_search("Python", self.workspace.id)

        result = results[0]
        assert result.document_id == self.document.id
        assert result.document_name == self.document.filename
        assert isinstance(result.similarity_score, float)
        assert 0 <= result.similarity_score <= 1

    def test_search_excludes_other_workspace(self):
        from apps.search.services import hybrid_search

        other_workspace = WorkspaceFactory()
        with patch("apps.search.services.generate_query_embedding", return_value=MOCK_EMBEDDING):
            results = hybrid_search("Python", other_workspace.id)

        assert all(r.document_id != self.document.id for r in results)

    def test_search_excludes_non_ready_documents(self):
        from apps.search.services import hybrid_search

        self.document.status = Document.Status.PROCESSING
        self.document.save()

        with patch("apps.search.services.generate_query_embedding", return_value=MOCK_EMBEDDING):
            results = hybrid_search("Python", self.workspace.id)

        assert all(r.document_id != self.document.id for r in results)

    def test_search_api_requires_auth(self, api_client):
        response = api_client.post(f"/api/workspaces/{self.workspace.id}/search/", {"query": "test"})
        assert response.status_code == 401

    def test_search_api_enforces_workspace_access(self, auth_client):
        other_workspace = WorkspaceFactory()
        with patch("apps.search.services.generate_query_embedding", return_value=MOCK_EMBEDDING):
            response = auth_client.post(f"/api/workspaces/{other_workspace.id}/search/", {"query": "test"})
        assert response.status_code == 403
