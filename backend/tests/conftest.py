import pytest
from rest_framework.test import APIClient

from apps.workspaces.models import WorkspaceMember
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMemberFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(db, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def workspace(db, user):
    ws = WorkspaceFactory(owner=user)
    WorkspaceMemberFactory(workspace=ws, user=user, role=WorkspaceMember.Role.OWNER)
    return ws


@pytest.fixture
def member_client(db):
    member = UserFactory()
    client = APIClient()
    client.force_authenticate(user=member)
    return client, member
