from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.http import HttpRequest


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields) -> "User":
        """Create and persist a regular user, normalising and requiring the email."""
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> "User":
        """Create a user with staff + superuser flags set."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.email


class AuditLog(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50)
    resource_id = models.BigIntegerField(null=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [models.Index(fields=["workspace_id", "created_at"])]

    def __str__(self) -> str:
        return f"{self.action} by {self.user_id} at {self.created_at}"


def create_audit_log(
    *,
    workspace_id: int,
    user: "User | None",
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    metadata: dict | None = None,
    request=None,
) -> None:
    """Write an audit-trail row, extracting client IP + user agent from request."""
    ip = None
    user_agent = ""
    if request:
        ip = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    AuditLog.objects.create(
        workspace_id=workspace_id,
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata or {},
        ip_address=ip,
        user_agent=user_agent,
    )


def _client_ip(request: HttpRequest) -> str | None:
    """Return the real client IP, honouring X-Forwarded-For only when the
    immediate peer is a configured trusted proxy.

    Trusting XFF unconditionally would let any caller spoof their IP; trusting
    it only when REMOTE_ADDR matches a known proxy keeps the audit trail honest.
    """
    trusted = set(getattr(settings, "TRUSTED_PROXY_IPS", []) or [])
    remote_addr = request.META.get("REMOTE_ADDR")
    if trusted and remote_addr in trusted:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            # First entry is the original client.
            return forwarded.split(",")[0].strip() or remote_addr
    return remote_addr
