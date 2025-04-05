from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.search.models import SearchQuery
from apps.search.services import SearchResult
from tests.factories import CollectionFactory, WorkspaceMemberFactory


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.mark.django_db
class TestSearchView:
    def test_search_returns_results_and_records_query(self):
        m = WorkspaceMemberFactory()
        fake = [SearchResult(1, 2, "doc.pdf", "content", 0, 0.9)]
        with patch("apps.search.views.hybrid_search", return_value=fake):
            r = client_for(m.user).post(f"/api/workspaces/{m.workspace_id}/search/", {"query": "python"})
        assert r.status_code == 200
        assert r.json()["meta"]["total"] == 1
        assert SearchQuery.objects.filter(workspace=m.workspace, query="python").exists()

    def test_search_with_collection_filter(self):
        m = WorkspaceMemberFactory()
        col = CollectionFactory(workspace=m.workspace)
        with patch("apps.search.views.hybrid_search", return_value=[]):
            r = client_for(m.user).post(
                f"/api/workspaces/{m.workspace_id}/search/",
                {"query": "x", "collection_id": col.id},
            )
        assert r.status_code == 200
        assert SearchQuery.objects.get(query="x").collection_id == col.id

    def test_empty_query_rejected(self):
        m = WorkspaceMemberFactory()
        r = client_for(m.user).post(f"/api/workspaces/{m.workspace_id}/search/", {"query": ""})
        assert r.status_code == 400
