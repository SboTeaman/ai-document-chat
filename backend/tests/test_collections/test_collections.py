import pytest
from rest_framework.test import APIClient

from apps.collections.models import Collection
from apps.workspaces.models import WorkspaceMember
from tests.factories import CollectionFactory, WorkspaceMemberFactory


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.mark.django_db
class TestCollections:
    def _admin(self):
        return WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)

    def test_list_collections(self):
        admin = self._admin()
        CollectionFactory(workspace=admin.workspace)
        r = client_for(admin.user).get(f"/api/workspaces/{admin.workspace_id}/collections/")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1
        assert r.json()["data"][0]["document_count"] == 0

    def test_member_can_list_but_not_create(self):
        member = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        r = client_for(member.user).post(f"/api/workspaces/{member.workspace_id}/collections/", {"name": "X"})
        assert r.status_code == 403

    def test_admin_creates_collection(self):
        admin = self._admin()
        r = client_for(admin.user).post(
            f"/api/workspaces/{admin.workspace_id}/collections/",
            {"name": "Policies", "description": "d"},
        )
        assert r.status_code == 201
        assert Collection.objects.filter(workspace=admin.workspace, name="Policies").exists()

    def test_create_validation_error(self):
        admin = self._admin()
        r = client_for(admin.user).post(f"/api/workspaces/{admin.workspace_id}/collections/", {})
        assert r.status_code == 400

    def test_detail_get(self):
        admin = self._admin()
        col = CollectionFactory(workspace=admin.workspace)
        r = client_for(admin.user).get(f"/api/workspaces/{admin.workspace_id}/collections/{col.id}/")
        assert r.status_code == 200
        assert r.json()["data"]["document_count"] == 0

    def test_patch_updates_collection(self):
        admin = self._admin()
        col = CollectionFactory(workspace=admin.workspace)
        r = client_for(admin.user).patch(
            f"/api/workspaces/{admin.workspace_id}/collections/{col.id}/",
            {"name": "Renamed"},
        )
        assert r.status_code == 200
        col.refresh_from_db()
        assert col.name == "Renamed"

    def test_delete_collection(self):
        admin = self._admin()
        col = CollectionFactory(workspace=admin.workspace)
        r = client_for(admin.user).delete(f"/api/workspaces/{admin.workspace_id}/collections/{col.id}/")
        assert r.status_code == 204
        assert not Collection.objects.filter(id=col.id).exists()

    def test_detail_missing_404(self):
        admin = self._admin()
        r = client_for(admin.user).get(f"/api/workspaces/{admin.workspace_id}/collections/999999/")
        assert r.status_code == 404
