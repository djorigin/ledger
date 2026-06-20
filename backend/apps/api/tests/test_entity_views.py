import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_entity, make_membership, make_user
from apps.entities.models import EntityRole

pytestmark = pytest.mark.django_db


def test_list_entities_returns_only_accessible_entities():
    user = make_user()
    accessible = make_entity("Mine")
    inaccessible = make_entity("Other")
    make_membership(user, accessible, EntityRole.VIEWER)

    client = authenticated_client(user)
    response = client.get("/api/v1/entities/")

    names = [e["name"] for e in response.data["results"]]
    assert names == ["Mine"]
    assert inaccessible.name not in names


def test_retrieve_entity_without_membership_returns_404():
    user = make_user()
    other_entity = make_entity("Other")

    client = authenticated_client(user)
    response = client.get(f"/api/v1/entities/{other_entity.id}/")

    assert response.status_code == 404


def test_unauthenticated_request_returns_401():
    client = APIClient()
    response = client.get("/api/v1/entities/")
    assert response.status_code == 401
