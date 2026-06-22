from datetime import date

import pytest

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import EntityRole
from apps.recurring.models import PendingRecurringEntry, RecurrenceFrequency, RecurringTransactionTemplate

pytestmark = pytest.mark.django_db


def _template_payload(entity, debit_account, credit_account):
    return {
        "entity": str(entity.id),
        "description": "Netflix subscription",
        "debit_account": str(debit_account.id),
        "credit_account": str(credit_account.id),
        "amount": "15.99",
        "currency": "AUD",
        "frequency": RecurrenceFrequency.MONTHLY,
        "start_date": "2026-01-01",
        "next_due_date": "2026-01-01",
    }


def _make_template_directly(entity, user, debit_account, credit_account):
    return RecurringTransactionTemplate.objects.create(
        entity=entity, description="Netflix subscription", debit_account=debit_account,
        credit_account=credit_account, amount="15.99", currency="AUD",
        frequency=RecurrenceFrequency.MONTHLY, start_date=date(2026, 1, 1),
        next_due_date=date(2026, 1, 1), created_by=user,
    )


def test_viewer_cannot_create_template():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/recurring-templates/", _template_payload(entity, groceries, bank), format="json"
    )
    assert response.status_code == 403


def test_editor_can_create_and_patch_template():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)

    client = authenticated_client(user)
    create = client.post(
        "/api/v1/recurring-templates/", _template_payload(entity, groceries, bank), format="json"
    )
    assert create.status_code == 201
    template_id = create.data["id"]

    patch = client.patch(f"/api/v1/recurring-templates/{template_id}/", {"is_active": False}, format="json")
    assert patch.status_code == 200
    assert patch.data["is_active"] is False


def test_cross_entity_template_returns_403():
    user = make_user()
    entity = make_entity()
    other_entity = make_entity("Other")
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(other_entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/recurring-templates/", _template_payload(other_entity, groceries, bank), format="json"
    )
    assert response.status_code == 403


def test_viewer_can_read_but_not_approve_pending_entry():
    editor = make_user("editor@example.com")
    viewer = make_user("viewer@example.com")
    entity = make_entity()
    make_membership(editor, entity, EntityRole.EDITOR)
    make_membership(viewer, entity, EntityRole.VIEWER)
    bank, groceries = make_accounts(entity)
    template = _make_template_directly(entity, editor, groceries, bank)
    pending = PendingRecurringEntry.objects.create(
        template=template, due_date=date(2026, 1, 1), amount="15.99"
    )

    viewer_client = authenticated_client(viewer)
    get_resp = viewer_client.get(f"/api/v1/recurring-pending/{pending.id}/")
    assert get_resp.status_code == 200

    approve_resp = viewer_client.post(f"/api/v1/recurring-pending/{pending.id}/approve/")
    assert approve_resp.status_code == 403


def test_no_membership_user_gets_404_for_pending_entry_detail():
    user = make_user()
    entity = make_entity()
    creator = make_user("creator@example.com")
    bank, groceries = make_accounts(entity)
    template = _make_template_directly(entity, creator, groceries, bank)
    pending = PendingRecurringEntry.objects.create(
        template=template, due_date=date(2026, 1, 1), amount="15.99"
    )
    # deliberately no membership for `user`

    client = authenticated_client(user)
    response = client.get(f"/api/v1/recurring-pending/{pending.id}/")
    assert response.status_code == 404


def test_editor_can_approve_and_dismiss_pending_entries():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    template = _make_template_directly(entity, user, groceries, bank)
    pending1 = PendingRecurringEntry.objects.create(
        template=template, due_date=date(2026, 1, 1), amount="15.99"
    )
    pending2 = PendingRecurringEntry.objects.create(
        template=template, due_date=date(2026, 2, 1), amount="15.99"
    )

    client = authenticated_client(user)
    approve_resp = client.post(f"/api/v1/recurring-pending/{pending1.id}/approve/")
    assert approve_resp.status_code == 200
    assert approve_resp.data["status"] == "APPROVED"
    assert approve_resp.data["journal_entry"] is not None

    dismiss_resp = client.post(f"/api/v1/recurring-pending/{pending2.id}/dismiss/")
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.data["status"] == "DISMISSED"
    assert dismiss_resp.data["journal_entry"] is None


def test_approve_with_amount_override():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    template = _make_template_directly(entity, user, groceries, bank)
    pending = PendingRecurringEntry.objects.create(
        template=template, due_date=date(2026, 1, 1), amount="15.99"
    )

    client = authenticated_client(user)
    response = client.post(
        f"/api/v1/recurring-pending/{pending.id}/approve/", {"amount": "18.99"}, format="json"
    )
    assert response.status_code == 200

    from decimal import Decimal

    from apps.ledger.services import get_account_balance

    assert get_account_balance(groceries) == Decimal("18.99")


def test_re_approving_already_reviewed_entry_returns_400():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    template = _make_template_directly(entity, user, groceries, bank)
    pending = PendingRecurringEntry.objects.create(
        template=template, due_date=date(2026, 1, 1), amount="15.99"
    )

    client = authenticated_client(user)
    client.post(f"/api/v1/recurring-pending/{pending.id}/approve/")
    response = client.post(f"/api/v1/recurring-pending/{pending.id}/approve/")
    assert response.status_code == 400
