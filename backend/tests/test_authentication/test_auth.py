import pytest

from tests.factories import UserFactory


@pytest.mark.django_db
class TestRegister:
    url = "/api/auth/register/"

    def test_register_success(self, api_client):
        response = api_client.post(
            self.url, {"email": "new@example.com", "full_name": "New User", "password": "StrongPass1!"}
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["user"]["email"] == "new@example.com"
        assert "access_token" in data

    def test_register_duplicate_email(self, api_client, db):
        UserFactory(email="taken@example.com")
        response = api_client.post(
            self.url, {"email": "taken@example.com", "full_name": "X", "password": "StrongPass1!"}
        )
        assert response.status_code == 400
        assert any("already exists" in e["message"] for e in response.json()["errors"])

    def test_register_weak_password(self, api_client):
        response = api_client.post(self.url, {"email": "x@x.com", "full_name": "X", "password": "short"})
        assert response.status_code == 400

    def test_register_missing_fields(self, api_client):
        response = api_client.post(self.url, {"email": "x@x.com"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    url = "/api/auth/login/"

    def test_login_success(self, api_client, db):
        UserFactory(email="login@example.com")
        response = api_client.post(self.url, {"email": "login@example.com", "password": "TestPass123!"})
        assert response.status_code == 200
        assert "access_token" in response.json()["data"]

    def test_login_wrong_password(self, api_client, db):
        UserFactory(email="wrong@example.com")
        response = api_client.post(self.url, {"email": "wrong@example.com", "password": "wrongpass"})
        assert response.status_code == 401

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post(self.url, {"email": "ghost@example.com", "password": "anything"})
        assert response.status_code == 401
        assert response.json()["errors"][0]["message"] == "Invalid credentials."

    def test_login_response_does_not_reveal_email_existence(self, api_client, db):
        UserFactory(email="real@example.com")
        r1 = api_client.post(self.url, {"email": "real@example.com", "password": "wrong"})
        r2 = api_client.post(self.url, {"email": "fake@example.com", "password": "wrong"})
        assert r1.json()["errors"][0]["message"] == r2.json()["errors"][0]["message"]


@pytest.mark.django_db
class TestMe:
    url = "/api/auth/me/"

    def test_me_authenticated(self, auth_client, user):
        response = auth_client.get(self.url)
        assert response.status_code == 200
        assert response.json()["data"]["email"] == user.email

    def test_me_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401
