import pytest

from apps.api.tests.helpers import authenticated_client, make_entity, make_membership, make_user
from apps.entities.models import EntityRole

pytestmark = pytest.mark.django_db


def _asset_payload(entity):
    return {
        "entity": str(entity.id),
        "name": "Mount Gambier House",
        "category": "PROPERTY",
        "acquisition_date": "2018-03-01",
        "acquisition_cost": "380000.00",
        "currency": "AUD",
    }


def test_viewer_cannot_create_asset_class():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)

    client = authenticated_client(user)
    response = client.post("/api/v1/asset-classes/", _asset_payload(entity), format="json")
    assert response.status_code == 403


def test_editor_can_create_asset_class_and_add_valuation():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    create = client.post("/api/v1/asset-classes/", _asset_payload(entity), format="json")
    assert create.status_code == 201
    asset_id = create.data["id"]

    valuation = client.post(
        f"/api/v1/asset-classes/{asset_id}/valuations/",
        {"valuation_date": "2026-01-01", "current_value": "490000.00", "currency": "AUD"},
        format="json",
    )
    assert valuation.status_code == 201

    get_resp = client.get(f"/api/v1/asset-classes/{asset_id}/")
    assert get_resp.data["latest_valuation"]["current_value"] == "490000.0000"


def test_viewer_can_read_but_not_add_valuation():
    editor = make_user("editor@example.com")
    viewer = make_user("viewer@example.com")
    entity = make_entity()
    make_membership(editor, entity, EntityRole.EDITOR)
    make_membership(viewer, entity, EntityRole.VIEWER)

    editor_client = authenticated_client(editor)
    asset_id = editor_client.post(
        "/api/v1/asset-classes/", _asset_payload(entity), format="json"
    ).data["id"]

    viewer_client = authenticated_client(viewer)
    get_resp = viewer_client.get(f"/api/v1/asset-classes/{asset_id}/valuations/")
    assert get_resp.status_code == 200

    post_resp = viewer_client.post(
        f"/api/v1/asset-classes/{asset_id}/valuations/",
        {"valuation_date": "2026-01-01", "current_value": "490000.00", "currency": "AUD"},
        format="json",
    )
    assert post_resp.status_code == 403


def test_cross_entity_asset_class_returns_403():
    user = make_user()
    entity = make_entity()
    other_entity = make_entity("Other")
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    response = client.post("/api/v1/asset-classes/", _asset_payload(other_entity), format="json")
    assert response.status_code == 403


def test_net_worth_summary_only_includes_accessible_entities():
    user_a = make_user("a@example.com")
    user_b = make_user("b@example.com")
    entity_a = make_entity("Household A")
    entity_b = make_entity("Household B")
    make_membership(user_a, entity_a, EntityRole.EDITOR)
    make_membership(user_b, entity_b, EntityRole.EDITOR)

    client_a = authenticated_client(user_a)
    client_a.post("/api/v1/asset-classes/", _asset_payload(entity_a), format="json")

    client_b = authenticated_client(user_b)
    client_b.post("/api/v1/asset-classes/", _asset_payload(entity_b), format="json")

    response = client_a.get("/api/v1/asset-classes/net-worth-summary/?reporting_currency=AUD")
    assert response.status_code == 200
    entity_ids = {row["entity_id"] for row in response.data["rows"]}
    assert str(entity_a.id) in entity_ids
    assert str(entity_b.id) not in entity_ids


def test_unauthenticated_request_returns_401():
    from rest_framework.test import APIClient

    client = APIClient()
    response = client.get("/api/v1/asset-classes/")
    assert response.status_code == 401
