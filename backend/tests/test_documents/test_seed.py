import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.collections.models import Collection
from apps.workspaces.models import Workspace

User = get_user_model()


@pytest.mark.django_db
class TestSeedDemo:
    def test_seed_creates_demo_data(self):
        call_command("seed_demo")
        assert User.objects.filter(email="demo@example.com").exists()
        assert Workspace.objects.filter(slug="demo-workspace").exists()
        assert Collection.objects.count() == 3

    def test_seed_is_idempotent(self):
        call_command("seed_demo")
        call_command("seed_demo")  # second run exercises the "already exists" branches
        assert User.objects.filter(email="demo@example.com").count() == 1
        assert Workspace.objects.filter(slug="demo-workspace").count() == 1
        assert Collection.objects.count() == 3
