from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "is_active", "is_staff", "created_at"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["email", "full_name"]
    ordering = ["-created_at"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("full_name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "resource_type", "resource_id", "user", "workspace", "created_at"]
    list_filter = ["action", "resource_type"]
    search_fields = ["user__email", "action"]
    readonly_fields = [
        "workspace",
        "user",
        "action",
        "resource_type",
        "resource_id",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    ]

    def has_add_permission(self, request):
        """Audit rows are written only by the app — never created via admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit log is append-only: editing existing rows is forbidden."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit log is append-only: deleting rows is forbidden."""
        return False
