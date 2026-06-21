import pytest
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_user

pytestmark = pytest.mark.django_db


def test_superannuation_projection_endpoint_returns_projected_balance():
    user = make_user()
    client = authenticated_client(user)
    response = client.post(
        "/api/v1/superannuation/project/",
        {
            "current_balance": "50000.00",
            "target_date": "2030-01-01",
            "annual_contribution": "10000.00",
            "annual_growth_rate": "0.07",
        },
        format="json",
    )
    assert response.status_code == 200
    assert "projected_balance" in response.data


def test_superannuation_projection_endpoint_rejects_past_target_date_with_400():
    user = make_user()
    client = authenticated_client(user)
    response = client.post(
        "/api/v1/superannuation/project/",
        {
            "current_balance": "50000.00",
            "target_date": "2020-01-01",
            "annual_contribution": "10000.00",
            "annual_growth_rate": "0.07",
        },
        format="json",
    )
    assert response.status_code == 400


def test_superannuation_projection_requires_authentication():
    client = APIClient()
    response = client.post("/api/v1/superannuation/project/", {}, format="json")
    assert response.status_code == 401
