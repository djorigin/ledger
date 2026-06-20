import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import (
    authenticated_client,
    make_accounts,
    make_entity,
    make_membership,
    make_user,
)
from apps.entities.models import EntityRole

pytestmark = pytest.mark.django_db


def test_list_accounts_scoped_to_accessible_entities():
    user = make_user()
    accessible_entity = make_entity("Mine")
    inaccessible_entity = make_entity("Other")
    make_membership(user, accessible_entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(accessible_entity)
    other_bank, _ = make_accounts(inaccessible_entity)

    client = authenticated_client(user)
    response = client.get("/api/v1/accounts/")

    ids = {a["id"] for a in response.data["results"]}
    assert str(bank.id) in ids
    assert str(groceries.id) in ids
    assert str(other_bank.id) not in ids


def test_retrieve_account_under_inaccessible_entity_returns_404():
    user = make_user()
    inaccessible_entity = make_entity("Other")
    other_bank, _ = make_accounts(inaccessible_entity)

    client = authenticated_client(user)
    response = client.get(f"/api/v1/accounts/{other_bank.id}/")

    assert response.status_code == 404


def test_unauthenticated_request_returns_401():
    client = APIClient()
    response = client.get("/api/v1/accounts/")
    assert response.status_code == 401
