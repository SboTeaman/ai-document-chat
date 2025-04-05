import pytest
from rest_framework.test import APIClient

from apps.authentication.models import AuditLog
from apps.workspaces.models import Workspace, WorkspaceMember
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMemberFactory


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.mark.django_db
class TestWorkspaceListCreate:
    def test_lists_only_member_workspaces(self):
        m = WorkspaceMemberFactory()
        WorkspaceFactory()  # someone else's workspace
        r = client_for(m.user).get("/api/workspaces/")
        assert r.status_code == 200
        ids = [w["id"] for w in r.json()["data"]]
        assert ids == [m.workspace_id]

    def test_create_makes_caller_owner(self):
        user = UserFactory()
        r = client_for(user).post("/api/workspaces/", {"name": "My WS"})
        assert r.status_code == 201
        ws = Workspace.objects.get(name="My WS")
        assert WorkspaceMember.objects.get(workspace=ws, user=user).role == WorkspaceMember.Role.OWNER

    def test_create_validation_error(self):
        r = client_for(UserFactory()).post("/api/workspaces/", {})
        assert r.status_code == 400


@pytest.mark.django_db
class TestWorkspaceDetail:
    def test_member_can_view(self):
        m = WorkspaceMemberFactory()
        r = client_for(m.user).get(f"/api/workspaces/{m.workspace_id}/")
        assert r.status_code == 200
        assert r.json()["data"]["my_role"] == m.role

    def test_missing_workspace_404(self):
        owner = WorkspaceMemberFactory(role=WorkspaceMember.Role.OWNER)
        # member of *a* workspace, asks for a different (nonexistent) id
        r = client_for(owner.user).get(f"/api/workspaces/{owner.workspace_id}/")
        assert r.status_code == 200  # sanity
        r404 = client_for(owner.user).get("/api/workspaces/999999/")
        assert r404.status_code == 403  # not a member of 999999 → permission denied first

    def test_owner_can_delete_and_it_is_audited(self):
        owner = WorkspaceMemberFactory(role=WorkspaceMember.Role.OWNER)
        r = client_for(owner.user).delete(f"/api/workspaces/{owner.workspace_id}/")
        assert r.status_code == 204
        assert not Workspace.objects.filter(id=owner.workspace_id).exists()
        assert AuditLog.objects.filter(action="workspace.delete").exists()

    def test_non_owner_cannot_delete(self):
        admin = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        r = client_for(admin.user).delete(f"/api/workspaces/{admin.workspace_id}/")
        assert r.status_code == 403


@pytest.mark.django_db
class TestMembers:
    def _admin(self):
        return WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)

    def test_list_members(self):
        admin = self._admin()
        r = client_for(admin.user).get(f"/api/workspaces/{admin.workspace_id}/members/")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1

    def test_invite_unknown_email_returns_202(self):
        admin = self._admin()
        r = client_for(admin.user).post(
            f"/api/workspaces/{admin.workspace_id}/members/", {"email": "ghost@example.com"}
        )
        assert r.status_code == 202

    def test_invite_existing_member_returns_202(self):
        admin = self._admin()
        existing = WorkspaceMemberFactory(workspace=admin.workspace)
        r = client_for(admin.user).post(
            f"/api/workspaces/{admin.workspace_id}/members/", {"email": existing.user.email}
        )
        assert r.status_code == 202

    def test_invite_new_user_creates_member_and_audits(self):
        admin = self._admin()
        invitee = UserFactory()
        r = client_for(admin.user).post(
            f"/api/workspaces/{admin.workspace_id}/members/",
            {"email": invitee.email, "role": "member"},
        )
        assert r.status_code == 201
        assert WorkspaceMember.objects.filter(workspace=admin.workspace, user=invitee).exists()
        assert AuditLog.objects.filter(action="member.invite").exists()

    def test_member_cannot_invite(self):
        member = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        r = client_for(member.user).post(f"/api/workspaces/{member.workspace_id}/members/", {"email": "x@example.com"})
        assert r.status_code == 403


@pytest.mark.django_db
class TestMemberDetail:
    def test_change_role_succeeds_and_audits(self):
        admin = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        target = WorkspaceMemberFactory(workspace=admin.workspace, role=WorkspaceMember.Role.MEMBER)
        r = client_for(admin.user).patch(
            f"/api/workspaces/{admin.workspace_id}/members/{target.id}/", {"role": "admin"}
        )
        assert r.status_code == 200
        target.refresh_from_db()
        assert target.role == WorkspaceMember.Role.ADMIN
        assert AuditLog.objects.filter(action="member.role_change").exists()

    def test_cannot_change_owner_role(self):
        owner = WorkspaceMemberFactory(role=WorkspaceMember.Role.OWNER)
        admin = WorkspaceMemberFactory(workspace=owner.workspace, role=WorkspaceMember.Role.ADMIN)
        r = client_for(admin.user).patch(
            f"/api/workspaces/{owner.workspace_id}/members/{owner.id}/", {"role": "member"}
        )
        assert r.status_code == 400
        assert r.json()["errors"][0]["code"] == "cannot_change_owner"

    def test_invalid_role_rejected(self):
        admin = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        target = WorkspaceMemberFactory(workspace=admin.workspace, role=WorkspaceMember.Role.MEMBER)
        r = client_for(admin.user).patch(
            f"/api/workspaces/{admin.workspace_id}/members/{target.id}/", {"role": "wizard"}
        )
        assert r.status_code == 400

    def test_remove_member_succeeds_and_audits(self):
        admin = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        target = WorkspaceMemberFactory(workspace=admin.workspace, role=WorkspaceMember.Role.MEMBER)
        r = client_for(admin.user).delete(f"/api/workspaces/{admin.workspace_id}/members/{target.id}/")
        assert r.status_code == 204
        assert not WorkspaceMember.objects.filter(id=target.id).exists()
        assert AuditLog.objects.filter(action="member.remove").exists()

    def test_cannot_remove_owner(self):
        owner = WorkspaceMemberFactory(role=WorkspaceMember.Role.OWNER)
        admin = WorkspaceMemberFactory(workspace=owner.workspace, role=WorkspaceMember.Role.ADMIN)
        r = client_for(admin.user).delete(f"/api/workspaces/{owner.workspace_id}/members/{owner.id}/")
        assert r.status_code == 400

    def test_missing_member_404(self):
        admin = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        r = client_for(admin.user).delete(f"/api/workspaces/{admin.workspace_id}/members/999999/")
        assert r.status_code == 404
