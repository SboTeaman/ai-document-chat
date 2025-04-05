from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.authentication.serializers import UserSerializer

from .models import Workspace, WorkspaceMember

User = get_user_model()


class WorkspaceSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "owner", "member_count", "my_role", "created_at"]
        read_only_fields = ["id", "slug", "owner", "member_count", "my_role", "created_at"]

    def get_member_count(self, obj):
        """Member count: prefer the annotated value, else fall back to a query."""
        annotated = getattr(obj, "member_count_annotated", None)
        if annotated is not None:
            return annotated
        return obj.members.count()

    def get_my_role(self, obj):
        """Return the requesting user's role in this workspace, or None.

        Requires the queryset to call prefetch_related('members') to avoid
        an extra query per workspace when serializing a list.
        """
        request = self.context.get("request")
        if request:
            membership = obj.members.filter(user=request.user).first()
            return membership.role if membership else None
        return None


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["name"]


class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ["id", "user", "role", "joined_at"]
        read_only_fields = ["id", "user", "joined_at"]


# OWNER is excluded: the owner slot is held by workspace creator only.
# Admins cannot elevate anyone (including themselves) to owner via the API.
_ASSIGNABLE_ROLE_CHOICES = [
    (WorkspaceMember.Role.ADMIN, "Admin"),
    (WorkspaceMember.Role.MEMBER, "Member"),
    (WorkspaceMember.Role.VIEWER, "Viewer"),
]


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=_ASSIGNABLE_ROLE_CHOICES, default=WorkspaceMember.Role.MEMBER)


class UpdateMemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=_ASSIGNABLE_ROLE_CHOICES)
