from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.utils.text import slugify


class Workspace(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_workspaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workspaces"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Persist the workspace, auto-generating a collision-safe unique slug."""
        if not self.slug:
            base_slug = slugify(self.name)
            counter = 0
            while True:
                self.slug = base_slug if counter == 0 else f"{base_slug}-{counter}"
                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    counter += 1
        else:
            super().save(*args, **kwargs)


class WorkspaceMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspace_members"
        unique_together = ["workspace", "user"]
        indexes = [models.Index(fields=["user", "workspace"])]

    def __str__(self):
        return f"{self.user.email} — {self.role} in {self.workspace.name}"
