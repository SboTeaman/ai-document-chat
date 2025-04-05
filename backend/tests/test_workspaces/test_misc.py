import pytest
from rest_framework.exceptions import NotFound

from apps.workspaces.models import Workspace
from apps.workspaces.views import WorkspaceDetailView
from tests.factories import UserFactory, WorkspaceFactory


@pytest.mark.django_db
class TestSlugGeneration:
    def test_duplicate_names_get_incrementing_slugs(self):
        WorkspaceFactory(name="Acme")
        ws2 = Workspace.objects.create(name="Acme", owner=UserFactory())
        ws3 = Workspace.objects.create(name="Acme", owner=UserFactory())
        assert ws2.slug == "acme-1"
        assert ws3.slug == "acme-2"


@pytest.mark.django_db
class TestGetWorkspaceHelper:
    def test_missing_workspace_raises_not_found(self):
        with pytest.raises(NotFound):
            WorkspaceDetailView()._get_workspace(999999)
