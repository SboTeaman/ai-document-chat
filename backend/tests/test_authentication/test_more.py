from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.services import logout_all_sessions
from tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserManager:
    def test_create_user_requires_email(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(email="", password="x")

    def test_create_user_normalises_email(self):
        user = User.objects.create_user(email="Mix@Example.COM", password="StrongPass1!")
        assert user.email == "Mix@example.com"

    def test_create_superuser_sets_flags(self):
        su = User.objects.create_superuser(email="root@example.com", password="StrongPass1!")
        assert su.is_staff and su.is_superuser


@pytest.mark.django_db
class TestLogoutAllSessions:
    def test_blacklists_all_outstanding_tokens(self):
        user = UserFactory()
        r1 = str(RefreshToken.for_user(user))
        r2 = str(RefreshToken.for_user(user))
        logout_all_sessions(user)
        # Both refresh tokens are now revoked.
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": r1}).status_code == 401
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": r2}).status_code == 401

    def test_tolerates_already_blacklisted_token(self):
        user = UserFactory()
        token = RefreshToken.for_user(user)
        token.blacklist()  # pre-blacklisted → triggers the TokenError branch
        logout_all_sessions(user)  # must not raise


@pytest.mark.django_db
class TestLogout:
    def test_logout_blacklists_own_token(self):
        user = UserFactory()
        refresh = str(RefreshToken.for_user(user))
        client = APIClient()
        client.force_authenticate(user)
        assert client.post("/api/auth/logout/", {"refresh_token": refresh}).status_code == 204
        # The blacklisted token can no longer be refreshed.
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": refresh}).status_code == 401

    def test_logout_ignores_token_belonging_to_another_user(self):
        owner = UserFactory()
        attacker = UserFactory()
        victim_refresh = str(RefreshToken.for_user(owner))
        client = APIClient()
        client.force_authenticate(attacker)
        assert client.post("/api/auth/logout/", {"refresh_token": victim_refresh}).status_code == 204
        # Victim's token must still be valid — attacker could not revoke it.
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": victim_refresh}).status_code == 200

    def test_logout_with_invalid_token_is_noop(self):
        client = APIClient()
        client.force_authenticate(UserFactory())
        assert client.post("/api/auth/logout/", {"refresh_token": "garbage"}).status_code == 204


@pytest.mark.django_db
class TestRefreshRotation:
    def test_refresh_rotates_and_old_token_is_revoked(self):
        user = UserFactory()
        refresh = str(RefreshToken.for_user(user))
        r1 = APIClient().post("/api/auth/token/refresh/", {"refresh_token": refresh})
        assert r1.status_code == 200
        new_refresh = r1.json()["data"]["refresh_token"]
        assert new_refresh != refresh
        # Old token is blacklisted; new one works.
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": refresh}).status_code == 401
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": new_refresh}).status_code == 200

    def test_refresh_with_invalid_token(self):
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": "garbage"}).status_code == 401

    def test_refresh_for_deleted_user(self):
        user = UserFactory()
        refresh = str(RefreshToken.for_user(user))
        user.delete()
        assert APIClient().post("/api/auth/token/refresh/", {"refresh_token": refresh}).status_code == 401


@pytest.mark.django_db
class TestChangePassword:
    url = "/api/auth/me/password/"

    def test_change_password_success(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user)
        r = client.post(self.url, {"current_password": "TestPass123!", "new_password": "BrandNewPass9!"})
        assert r.status_code == 204
        user.refresh_from_db()
        assert user.check_password("BrandNewPass9!")

    def test_change_password_wrong_current(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user)
        r = client.post(self.url, {"current_password": "nope", "new_password": "BrandNewPass9!"})
        assert r.status_code == 400
        assert r.json()["errors"][0]["code"] == "wrong_password"

    def test_change_password_weak_new(self):
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user)
        r = client.post(self.url, {"current_password": "TestPass123!", "new_password": "123"})
        assert r.status_code == 400


@pytest.mark.django_db
class TestHealth:
    def test_ok(self):
        r = APIClient().get("/health/")
        assert r.status_code == 200
        assert r.json()["checks"] == {"database": True, "redis": True}

    def test_redis_down_returns_503(self):
        with patch("apps.authentication.health_views.cache.set", side_effect=Exception("down")):
            r = APIClient().get("/health/")
        assert r.status_code == 503
        assert r.json()["status"] == "degraded"

    def test_database_down_returns_503(self):
        with patch(
            "apps.authentication.health_views.connection.ensure_connection",
            side_effect=Exception("down"),
        ):
            r = APIClient().get("/health/")
        assert r.status_code == 503

    def test_deep_mode_success(self):
        with (
            patch("urllib.request.urlopen") as mock_open,
            patch("common.storage.get_s3_client") as mock_s3,
        ):
            mock_open.return_value.__enter__.return_value.status = 200
            mock_s3.return_value.head_bucket.return_value = {}
            r = APIClient().get("/health/?deep=1")
        assert r.status_code == 200
        body = r.json()["checks"]
        assert body["ollama"] is True and body["storage"] is True

    def test_deep_mode_failure(self):
        with (
            patch("urllib.request.urlopen", side_effect=Exception("no ollama")),
            patch("common.storage.get_s3_client", side_effect=Exception("no s3")),
        ):
            r = APIClient().get("/health/?deep=1")
        assert r.status_code == 503
        assert r.json()["checks"]["ollama"] is False
