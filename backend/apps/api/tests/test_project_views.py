import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole

pytestmark = pytest.mark.django_db


def _project_payload(entity):
    return {
        "entity": str(entity.id),
        "name": "China migration costs",
        "budget_amount": "5000.00",
        "currency": "AUD",
        "status": "ACTIVE",
    }


def test_viewer_cannot_create_project():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)

    client = authenticated_client(user)
    response = client.post("/api/v1/projects/", _project_payload(entity), format="json")
    assert response.status_code == 403


def test_editor_can_create_project():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)

    client = authenticated_client(user)
    response = client.post("/api/v1/projects/", _project_payload(entity), format="json")
    assert response.status_code == 201


def test_project_progress_endpoint_returns_actual_to_date():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    project_resp = client.post("/api/v1/projects/", _project_payload(entity), format="json")
    project_id = project_resp.data["id"]

    response = client.get(f"/api/v1/projects/{project_id}/progress/")
    assert response.status_code == 200
    assert response.data["actual_to_date"] == "0.0000"


def test_journal_entry_create_with_project_tag_visible_in_project_progress():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    project_resp = client.post("/api/v1/projects/", _project_payload(entity), format="json")
    project_id = project_resp.data["id"]

    entry_payload = {
        "entity": str(entity.id),
        "entry_date": "2026-01-01",
        "description": "Visa fees",
        "project": project_id,
        "lines": [
            {"account": str(groceries.id), "currency": "AUD", "debit_amount": "300.00"},
            {"account": str(bank.id), "currency": "AUD", "credit_amount": "300.00"},
        ],
    }
    create = client.post("/api/v1/journal-entries/", entry_payload, format="json")
    assert create.status_code == 201
    assert str(create.data["project"]) == project_id

    progress = client.get(f"/api/v1/projects/{project_id}/progress/")
    assert progress.data["actual_to_date"] == "300.0000"


def test_unauthenticated_request_returns_401():
    client = APIClient()
    response = client.get("/api/v1/projects/")
    assert response.status_code == 401
