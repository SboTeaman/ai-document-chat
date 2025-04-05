import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import create_audit_log
from common.pagination import MemberPagination, WorkspacePagination
from common.permissions import CanManageWorkspace, IsWorkspaceMember, IsWorkspaceOwner

from .models import Workspace, WorkspaceMember
from .serializers import (
    InviteMemberSerializer,
    MemberSerializer,
    UpdateMemberRoleSerializer,
    WorkspaceCreateSerializer,
    WorkspaceSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class WorkspaceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List the workspaces the caller belongs to, with member counts."""
        workspace_ids = WorkspaceMember.objects.filter(user=request.user).values_list("workspace_id", flat=True)
        workspaces = (
            Workspace.objects.filter(id__in=workspace_ids)
            .select_related("owner")
            .annotate(member_count_annotated=Count("members"))
        )
        paginator = WorkspacePagination()
        page = paginator.paginate_queryset(workspaces, request)
        serializer = WorkspaceSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a workspace and make the caller its Owner (atomically)."""
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            workspace = serializer.save(owner=request.user)
            WorkspaceMember.objects.create(workspace=workspace, user=request.user, role=WorkspaceMember.Role.OWNER)
        logger.info("Workspace created", extra={"workspace_id": workspace.id, "user_id": request.user.id})
        return Response(
            {"data": WorkspaceSerializer(workspace, context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )


class WorkspaceDetailView(APIView):
    def get_permissions(self):
        """Only the Owner may delete; any member may read."""
        if self.request.method == "DELETE":
            return [IsWorkspaceOwner()]
        return [IsWorkspaceMember()]

    def get(self, request, workspace_id):
        workspace = self._get_workspace(workspace_id)
        return Response({"data": WorkspaceSerializer(workspace, context={"request": request}).data})

    def delete(self, request, workspace_id):
        """Delete the workspace (Owner only), writing an audit row first."""
        workspace = self._get_workspace(workspace_id)
        # Log before deletion. The AuditLog.workspace FK is SET_NULL, so the row
        # survives the cascade with the name preserved in metadata for the trail.
        create_audit_log(
            workspace_id=workspace_id,
            user=request.user,
            action="workspace.delete",
            resource_type="workspace",
            resource_id=workspace_id,
            metadata={"name": workspace.name},
            request=request,
        )
        workspace.delete()
        logger.info("Workspace deleted", extra={"workspace_id": workspace_id, "user_id": request.user.id})
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_workspace(self, workspace_id):
        """Fetch a workspace by id or raise 404."""
        try:
            return Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            raise NotFound() from None


class WorkspaceMembersView(APIView):
    def get_permissions(self):
        """Admin/Owner may invite; any member may list."""
        if self.request.method == "POST":
            return [CanManageWorkspace()]
        return [IsWorkspaceMember()]

    def get(self, request, workspace_id):
        members = WorkspaceMember.objects.filter(workspace_id=workspace_id).select_related("user")
        paginator = MemberPagination()
        page = paginator.paginate_queryset(members, request)
        return paginator.get_paginated_response(MemberSerializer(page, many=True).data)

    def post(self, request, workspace_id):
        """Invite a user by email; never leaks whether the email exists or is already a member."""
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Do not leak whether the email maps to an existing account.
        # Return 202 in all "no-op" cases (unknown user, already a member),
        # only differentiating on successful creation.
        accepted_response = Response(
            {"data": {"status": "accepted"}},
            status=status.HTTP_202_ACCEPTED,
        )

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is None:
            logger.info(
                "Invite to unknown email",
                extra={"workspace_id": workspace_id, "actor_id": request.user.id},
            )
            return accepted_response

        if WorkspaceMember.objects.filter(workspace_id=workspace_id, user=user).exists():
            return accepted_response

        member = WorkspaceMember.objects.create(
            workspace_id=workspace_id,
            user=user,
            role=serializer.validated_data["role"],
        )
        create_audit_log(
            workspace_id=workspace_id,
            user=request.user,
            action="member.invite",
            resource_type="workspace_member",
            resource_id=member.id,
            metadata={"invited_user_id": user.id},
            request=request,
        )
        return Response({"data": MemberSerializer(member).data}, status=status.HTTP_201_CREATED)


class WorkspaceMemberDetailView(APIView):
    permission_classes = [CanManageWorkspace]

    def patch(self, request, workspace_id, member_id):
        """Change a member's role (Admin/Owner). The Owner's role is immutable."""
        member = self._get_member(workspace_id, member_id)
        if member.role == WorkspaceMember.Role.OWNER:
            return Response(
                {"errors": [{"code": "cannot_change_owner", "message": "Cannot change owner role.", "field": None}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_role = member.role
        member.role = serializer.validated_data["role"]
        member.save(update_fields=["role"])
        create_audit_log(
            workspace_id=workspace_id,
            user=request.user,
            action="member.role_change",
            resource_type="workspace_member",
            resource_id=member.id,
            metadata={"target_user_id": member.user_id, "from": old_role, "to": member.role},
            request=request,
        )
        return Response({"data": MemberSerializer(member).data})

    def delete(self, request, workspace_id, member_id):
        """Remove a member (Admin/Owner). The Owner cannot be removed."""
        member = self._get_member(workspace_id, member_id)
        if member.role == WorkspaceMember.Role.OWNER:
            return Response(
                {"errors": [{"code": "cannot_remove_owner", "message": "Cannot remove owner.", "field": None}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        create_audit_log(
            workspace_id=workspace_id,
            user=request.user,
            action="member.remove",
            resource_type="workspace_member",
            resource_id=member_id,
            request=request,
        )
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_member(self, workspace_id, member_id):
        """Fetch a membership row scoped to the workspace, or raise 404."""
        try:
            return WorkspaceMember.objects.get(workspace_id=workspace_id, id=member_id)
        except WorkspaceMember.DoesNotExist:
            raise NotFound() from None
