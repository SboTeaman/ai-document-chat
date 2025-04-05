from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.collections.models import Collection
from apps.workspaces.models import Workspace, WorkspaceMember

User = get_user_model()

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo1234!"  # noqa: S105 — intentional demo seed credential, documented in README


class Command(BaseCommand):
    help = "Seed demo workspace, user, and collections for local development"

    def handle(self, *args, **options):
        """Idempotently create the demo user, workspace, and starter collections."""
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=DEMO_EMAIL,
                defaults={"full_name": "Demo User", "is_staff": True},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}"))
            else:
                self.stdout.write(f"Demo user already exists: {DEMO_EMAIL}")

            workspace, created = Workspace.objects.get_or_create(
                slug="demo-workspace",
                defaults={"name": "Demo Workspace", "owner": user},
            )
            if created:
                WorkspaceMember.objects.create(workspace=workspace, user=user, role=WorkspaceMember.Role.OWNER)
                self.stdout.write(self.style.SUCCESS("Created demo workspace"))

            for name, desc in [
                ("Company Policies", "HR policies, code of conduct, and company guidelines"),
                ("Technical Docs", "API documentation, architecture decisions, runbooks"),
                ("Product", "Product specs, roadmaps, feature descriptions"),
            ]:
                Collection.objects.get_or_create(workspace=workspace, name=name, defaults={"description": desc})

            self.stdout.write(self.style.SUCCESS("\nDemo seed complete!"))
            self.stdout.write("  API:        http://localhost:8000/api/docs/")
            self.stdout.write("  Frontend:   http://localhost:5173")
            self.stdout.write(f"  Login:      {DEMO_EMAIL} / {DEMO_PASSWORD}")
            self.stdout.write("  Admin:      http://localhost:8000/admin/")
            self.stdout.write("  Flower:     http://localhost:5555")
            self.stdout.write("  MinIO:      http://localhost:9001")
