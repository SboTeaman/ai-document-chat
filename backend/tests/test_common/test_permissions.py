from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.workspaces.models import WorkspaceMember
from common import permissions
from tests.factories import (
    DocumentFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


def _req(user):
    return SimpleNamespace(user=user)


def _view(workspace_id):
    return SimpleNamespace(kwargs={"workspace_id": workspace_id})


@pytest.mark.django_db
class TestGetMembership:
    def test_anonymous_user_returns_none(self):
        assert permissions.get_membership(AnonymousUser(), 1) is None

    def test_non_member_returns_none(self):
        ws = WorkspaceFactory()
        assert permissions.get_membership(UserFactory(), ws.id) is None

    def test_member_returns_membership(self):
        m = WorkspaceMemberFactory()
        assert permissions.get_membership(m.user, m.workspace_id) == m


@pytest.mark.django_db
class TestRolePermissions:
    def test_is_workspace_member(self):
        m = WorkspaceMemberFactory(role=WorkspaceMember.Role.VIEWER)
        perm = permissions.IsWorkspaceMember()
        assert perm.has_permission(_req(m.user), _view(m.workspace_id)) is True
        assert perm.has_permission(_req(UserFactory()), _view(m.workspace_id)) is False

    def test_can_upload_requires_member_or_higher(self):
        perm = permissions.CanUploadDocuments()
        viewer = WorkspaceMemberFactory(role=WorkspaceMember.Role.VIEWER)
        member = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        assert perm.has_permission(_req(viewer.user), _view(viewer.workspace_id)) is False
        assert perm.has_permission(_req(member.user), _view(member.workspace_id)) is True

    def test_can_manage_requires_admin_or_owner(self):
        perm = permissions.CanManageWorkspace()
        member = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        admin = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        assert perm.has_permission(_req(member.user), _view(member.workspace_id)) is False
        assert perm.has_permission(_req(admin.user), _view(admin.workspace_id)) is True

    def test_is_workspace_owner(self):
        perm = permissions.IsWorkspaceOwner()
        owner = WorkspaceMemberFactory(role=WorkspaceMember.Role.OWNER)
        admin = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        assert perm.has_permission(_req(owner.user), _view(owner.workspace_id)) is True
        assert perm.has_permission(_req(admin.user), _view(admin.workspace_id)) is False


@pytest.mark.django_db
class TestCanDeleteDocument:
    def test_non_member_denied(self):
        doc = DocumentFactory()
        perm = permissions.CanDeleteDocument()
        assert perm.has_object_permission(_req(UserFactory()), _view(doc.workspace_id), doc) is False

    def test_admin_can_delete_any(self):
        m = WorkspaceMemberFactory(role=WorkspaceMember.Role.ADMIN)
        doc = DocumentFactory(workspace=m.workspace)
        perm = permissions.CanDeleteDocument()
        assert perm.has_object_permission(_req(m.user), _view(m.workspace_id), doc) is True

    def test_member_can_delete_only_own(self):
        m = WorkspaceMemberFactory(role=WorkspaceMember.Role.MEMBER)
        own = DocumentFactory(workspace=m.workspace, uploaded_by=m.user)
        other = DocumentFactory(workspace=m.workspace, uploaded_by=UserFactory())
        perm = permissions.CanDeleteDocument()
        assert perm.has_object_permission(_req(m.user), _view(m.workspace_id), own) is True
        assert perm.has_object_permission(_req(m.user), _view(m.workspace_id), other) is False
