from unittest.mock import patch

import pytest
from django.contrib import admin as dj_admin
from rest_framework.exceptions import ValidationError

from apps.authentication.admin import AuditLogAdmin
from apps.authentication.models import AuditLog
from apps.authentication.serializers import RegisterSerializer
from tests.factories import UserFactory


class TestAuditLogAdmin:
    def test_audit_log_is_append_only(self):
        admin = AuditLogAdmin(AuditLog, dj_admin.site)
        assert admin.has_add_permission(None) is False
        assert admin.has_change_permission(None) is False
        assert admin.has_delete_permission(None) is False


@pytest.mark.django_db
class TestRegisterValidation:
    def test_common_password_rejected(self):
        serializer = RegisterSerializer()
        # Bypass Django's validators so the custom common-password check is reached.
        with patch("apps.authentication.serializers.validate_password"):
            with pytest.raises(ValidationError, match="too common"):
                serializer.validate_password("password1")

    def test_duplicate_email_rejected(self):
        UserFactory(email="dupe@example.com")
        with pytest.raises(ValidationError, match="already exists"):
            RegisterSerializer().validate_email("dupe@example.com")

    def test_email_is_normalised(self):
        assert RegisterSerializer().validate_email("New@Example.COM") == "new@example.com"
