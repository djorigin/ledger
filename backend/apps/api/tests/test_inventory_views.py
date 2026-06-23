import io

import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_entity, make_membership, make_user
from apps.entities.models import EntityRole

pytestmark = pytest.mark.django_db


def _item_payload(entity):
    return {
        "entity": str(entity.id),
        "name": "Sony A7IV",
        "category": "ELECTRONICS",
        "estimated_replacement_value": "4500.00",
        "currency": "AUD",
    }


def test_viewer_cannot_create_inventory_item():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)

    client = authenticated_client(user)
    response = client.post("/api/v1/inventory/", _item_payload(entity), format="json")
    assert response.status_code == 403


def test_editor_can_create_inventory_item():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    response = client.post("/api/v1/inventory/", _item_payload(entity), format="json")
    assert response.status_code == 201
    assert response.data["is_active"] is True


def test_multipart_create_defaults_is_active_true_even_when_omitted():
    """
    Regression test: DRF's BooleanField treats an absent multipart key as
    an unchecked HTML checkbox (False) on a non-partial write, which would
    otherwise silently create every photo-uploaded item already
    deactivated. InventoryItemSerializer.create() forces this to True.
    """
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    payload = _item_payload(entity)
    # multipart, not JSON -- is_active deliberately omitted, same as a
    # real photo upload would do
    response = client.post("/api/v1/inventory/", payload, format="multipart")
    assert response.status_code == 201
    assert response.data["is_active"] is True


def test_photo_upload_via_multipart():
    from PIL import Image

    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    buf.name = "test.jpg"

    client = authenticated_client(user)
    payload = {**_item_payload(entity), "photo": buf}
    response = client.post("/api/v1/inventory/", payload, format="multipart")
    assert response.status_code == 201
    assert response.data["photo"] is not None
    assert "test" in response.data["photo"]


def test_patch_can_deactivate_item():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    item_id = client.post("/api/v1/inventory/", _item_payload(entity), format="json").data["id"]

    response = client.patch(f"/api/v1/inventory/{item_id}/", {"is_active": False}, format="json")
    assert response.status_code == 200
    assert response.data["is_active"] is False


def test_summary_groups_by_category_and_excludes_inactive():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    client.post("/api/v1/inventory/", _item_payload(entity), format="json")
    inactive_id = client.post(
        "/api/v1/inventory/",
        {**_item_payload(entity), "name": "Old phone", "estimated_replacement_value": "200.00"},
        format="json",
    ).data["id"]
    client.patch(f"/api/v1/inventory/{inactive_id}/", {"is_active": False}, format="json")

    response = client.get(f"/api/v1/inventory/summary/?entity={entity.id}")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["category"] == "ELECTRONICS"
    assert response.data[0]["total_replacement_value"] == "4500.0000"
    assert response.data[0]["item_count"] == 1


def test_cross_entity_inventory_item_returns_403():
    user = make_user()
    entity = make_entity()
    other_entity = make_entity("Other")
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    response = client.post("/api/v1/inventory/", _item_payload(other_entity), format="json")
    assert response.status_code == 403


def test_unauthenticated_request_returns_401():
    client = APIClient()
    response = client.get("/api/v1/inventory/")
    assert response.status_code == 401
