from types import SimpleNamespace

import pytest

from apps.workspaces.serializers import WorkspaceSerializer
from tests.factories import UserFactory, WorkspaceFactory


@pytest.mark.django_db
class TestWorkspaceSerializer:
    def test_my_role_is_none_without_request(self):
        ws = WorkspaceFactory()
        assert WorkspaceSerializer(ws).data["my_role"] is None

    def test_my_role_is_none_for_non_member(self):
        ws = WorkspaceFactory()
        req = SimpleNamespace(user=UserFactory())
        assert WorkspaceSerializer(ws, context={"request": req}).data["my_role"] is None

    def test_member_count_falls_back_to_query_without_annotation(self):
        ws = WorkspaceFactory()
        assert WorkspaceSerializer(ws).data["member_count"] == 0
