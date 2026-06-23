import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import make_entity, make_membership, make_user
from apps.api_tokens.models import APIToken
from apps.entities.models import EntityRole

pytestmark = pytest.mark.django_db


def test_valid_token_authenticates_as_created_by():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    token, plaintext = APIToken.generate(name="Sheets sync", created_by=user)

    client = APIClient()
    response = client.get(
        f"/api/v1/reports/trial-balance/?entity={entity.id}", HTTP_AUTHORIZATION=f"Token {plaintext}"
    )
    assert response.status_code == 200


def test_garbage_token_returns_401():
    client = APIClient()
    response = client.get(
        "/api/v1/reports/net-worth/?reporting_currency=AUD", HTTP_AUTHORIZATION="Token not-a-real-token"
    )
    assert response.status_code == 401


def test_token_authenticated_write_returns_403():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    token, plaintext = APIToken.generate(name="Sheets sync", created_by=user)

    client = APIClient()
    response = client.post(
        "/api/v1/budgets/",
        {"entity": str(entity.id), "name": "test"},
        format="json",
        HTTP_AUTHORIZATION=f"Token {plaintext}",
    )
    assert response.status_code == 403


def test_token_authenticated_read_still_works_for_editor():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    token, plaintext = APIToken.generate(name="Sheets sync", created_by=user)

    client = APIClient()
    response = client.get(f"/api/v1/budgets/?entity={entity.id}", HTTP_AUTHORIZATION=f"Token {plaintext}")
    assert response.status_code == 200


def test_existing_jwt_auth_is_unaffected():
    """force_authenticate exercises DRF's normal session/JWT-style auth
    path -- confirms adding APITokenAuthentication to the authenticator
    list doesn't break it."""
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/v1/recurring-templates/",
        {
            "entity": str(entity.id), "description": "test", "amount": "10.00", "currency": "AUD",
            "frequency": "MONTHLY", "start_date": "2026-01-01", "next_due_date": "2026-01-01",
        },
        format="json",
    )
    # Validation may fail on missing required account fields, but the
    # point is it's NOT a 403 from DenyWriteForApiToken -- JWT/session auth
    # (force_authenticate) was never authenticated via APITokenAuthentication.
    assert response.status_code != 403


def test_last_used_at_updates_on_successful_authentication():
    user = make_user()
    token, plaintext = APIToken.generate(name="Sheets sync", created_by=user)
    assert token.last_used_at is None

    client = APIClient()
    client.get("/api/v1/reports/net-worth/?reporting_currency=AUD", HTTP_AUTHORIZATION=f"Token {plaintext}")

    token.refresh_from_db()
    assert token.last_used_at is not None


def test_token_hash_never_stores_plaintext():
    user = make_user()
    token, plaintext = APIToken.generate(name="Sheets sync", created_by=user)
    assert token.token_hash != plaintext
    assert plaintext not in token.token_hash
    assert token.token_prefix == plaintext[:8]
