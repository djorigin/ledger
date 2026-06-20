import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_entity, make_membership, make_user
from apps.entities.models import EntityRole

pytestmark = pytest.mark.django_db


def test_login_succeeds_with_valid_credentials():
    make_user(email="alice@example.com")
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/", {"email": "alice@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_login_fails_with_bad_password():
    make_user(email="alice@example.com")
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/", {"email": "alice@example.com", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_login_fails_with_unknown_email():
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/", {"email": "nobody@example.com", "password": "x"}
    )
    assert response.status_code == 401


def test_refresh_returns_new_access_token():
    make_user(email="alice@example.com")
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/", {"email": "alice@example.com", "password": "testpass123"}
    )
    response = client.post("/api/v1/auth/refresh/", {"refresh": login.data["refresh"]})
    assert response.status_code == 200
    assert "access" in response.data


def test_refresh_rotates_and_blacklists_old_token():
    make_user(email="alice@example.com")
    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/", {"email": "alice@example.com", "password": "testpass123"}
    )
    original_refresh = login.data["refresh"]

    first_refresh = client.post("/api/v1/auth/refresh/", {"refresh": original_refresh})
    assert first_refresh.status_code == 200
    assert first_refresh.data["refresh"] != original_refresh

    reuse_attempt = client.post("/api/v1/auth/refresh/", {"refresh": original_refresh})
    assert reuse_attempt.status_code == 401


def test_me_endpoint_returns_current_user_and_memberships():
    user = make_user(email="alice@example.com")
    household = make_entity("Smith Household")
    business = make_entity("Freelance Co")
    make_membership(user, household, EntityRole.OWNER)
    make_membership(user, business, EntityRole.VIEWER)

    client = authenticated_client(user)
    response = client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assert response.data["email"] == "alice@example.com"
    roles_by_entity = {m["entity_name"]: m["role"] for m in response.data["memberships"]}
    assert roles_by_entity == {"Smith Household": "OWNER", "Freelance Co": "VIEWER"}


def test_me_endpoint_requires_authentication():
    client = APIClient()
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == 401


def test_full_login_then_authenticated_request_flow():
    user = make_user(email="alice@example.com")
    entity = make_entity("Smith Household")
    make_membership(user, entity, EntityRole.OWNER)

    client = APIClient()
    login = client.post(
        "/api/v1/auth/login/", {"email": "alice@example.com", "password": "testpass123"}
    )
    access = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/api/v1/entities/")
    assert response.status_code == 200
    assert response.data["results"][0]["name"] == "Smith Household"
