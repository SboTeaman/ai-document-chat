from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.workspaces.models import WorkspaceMember


def get_membership(user, workspace_id: int) -> WorkspaceMember | None:
    """Return the user's ``WorkspaceMember`` row for a workspace, or ``None``.

    Used by every workspace permission class to resolve the caller's role.
    """
    # Anonymous users have no pk; filtering on one would raise a 500 trying to
    # cast AnonymousUser to int. Short-circuit so DRF returns 401/403 cleanly.
    if not user or not user.is_authenticated:
        return None
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


class IsWorkspaceMember(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        workspace_id = view.kwargs.get("workspace_id")
        return get_membership(request.user, workspace_id) is not None


class CanUploadDocuments(BasePermission):
    """Member, Admin, Owner can upload."""

    ALLOWED_ROLES = {
        WorkspaceMember.Role.MEMBER,
        WorkspaceMember.Role.ADMIN,
        WorkspaceMember.Role.OWNER,
    }

    def has_permission(self, request: Request, view) -> bool:
        workspace_id = view.kwargs.get("workspace_id")
        membership = get_membership(request.user, workspace_id)
        return membership is not None and membership.role in self.ALLOWED_ROLES


class CanManageWorkspace(BasePermission):
    """Admin and Owner only."""

    ALLOWED_ROLES = {WorkspaceMember.Role.ADMIN, WorkspaceMember.Role.OWNER}

    def has_permission(self, request: Request, view) -> bool:
        workspace_id = view.kwargs.get("workspace_id")
        membership = get_membership(request.user, workspace_id)
        return membership is not None and membership.role in self.ALLOWED_ROLES


class IsWorkspaceOwner(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        workspace_id = view.kwargs.get("workspace_id")
        membership = get_membership(request.user, workspace_id)
        return membership is not None and membership.role == WorkspaceMember.Role.OWNER


class CanDeleteDocument(BasePermission):
    """Admin/Owner can delete any doc; Member only their own."""

    ADMIN_ROLES = {WorkspaceMember.Role.ADMIN, WorkspaceMember.Role.OWNER}

    def has_object_permission(self, request: Request, view, obj) -> bool:
        workspace_id = view.kwargs.get("workspace_id")
        membership = get_membership(request.user, workspace_id)
        if membership is None:
            return False
        if membership.role in self.ADMIN_ROLES:
            return True
        return obj.uploaded_by == request.user
