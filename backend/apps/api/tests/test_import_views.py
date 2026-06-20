from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.api.tests.helpers import authenticated_client, make_accounts, make_entity, make_membership, make_user
from apps.entities.models import Entity, EntityRole, EntityType
from apps.imports.models import ImportedTransaction, ImportFileFormat
from apps.imports.services import confirm_import
from apps.ledger.models import Account, AccountType
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db


def _csv_file(rows, name="statement.csv"):
    header = "Date,Description,Debit,Credit\n"
    body = "".join(f"{d},{desc},{debit},{credit}\n" for d, desc, debit, credit in rows)
    return SimpleUploadedFile(name, (header + body).encode(), content_type="text/csv")


MAPPING_FORM_FIELDS = {
    "date_column": "Date",
    "date_format": "%d/%m/%Y",
    "description_column": "Description",
    "amount_convention": "DEBIT_CREDIT",
    "debit_column": "Debit",
    "credit_column": "Credit",
}


def test_viewer_cannot_preview_import():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/import-batches/preview/",
        {"account": str(bank.id), "file_format": "CSV", "file": _csv_file([("01/06/2026", "X", "10", "")])},
        format="multipart",
    )
    assert response.status_code == 403


def test_viewer_cannot_confirm_import():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.VIEWER)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/import-batches/confirm/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("01/06/2026", "X", "10", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    assert response.status_code == 403


def test_editor_can_preview_and_confirm_import():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    preview = client.post(
        "/api/v1/import-batches/preview/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("01/06/2026", "Groceries", "25.50", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    assert preview.status_code == 200
    assert preview.data["mapped"] is True
    assert preview.data["total_row_count"] == 1

    confirm = client.post(
        "/api/v1/import-batches/confirm/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("01/06/2026", "Groceries", "25.50", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    assert confirm.status_code == 201
    assert confirm.data["row_count"] == 1


def test_unauthenticated_request_returns_401():
    client = APIClient()
    response = client.post("/api/v1/import-batches/preview/", {}, format="multipart")
    assert response.status_code == 401


def test_preview_csv_without_mapping_returns_headers_for_mapping_ui():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/import-batches/preview/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("01/06/2026", "Groceries", "25.50", "")]),
        },
        format="multipart",
    )
    assert response.status_code == 200
    assert response.data["mapped"] is False
    assert "Date" in response.data["headers"]


def test_preview_csv_with_mapping_returns_mapped_preview_rows():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    response = client.post(
        "/api/v1/import-batches/preview/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("01/06/2026", "Groceries", "25.50", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    assert response.status_code == 200
    assert response.data["mapped"] is True
    assert response.data["preview_rows"][0]["description"] == "Groceries"


def test_confirm_import_creates_batch_visible_in_list_endpoint():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)

    client = authenticated_client(user)
    client.post(
        "/api/v1/import-batches/confirm/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("01/06/2026", "Groceries", "25.50", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    response = client.get(f"/api/v1/import-batches/?account={bank.id}")
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_list_import_batches_filtered_to_accessible_accounts():
    user = make_user()
    accessible_entity = make_entity("Mine")
    inaccessible_entity = make_entity("Other")
    make_membership(user, accessible_entity, EntityRole.EDITOR)
    accessible_bank, _ = make_accounts(accessible_entity)
    inaccessible_bank, _ = make_accounts(inaccessible_entity)

    other_user = make_user(email="other@example.com")
    # Built directly via the service layer (not the API) since other_user
    # has no membership on inaccessible_entity and so couldn't pass the
    # create-permission check via the API anyway.
    confirm_import(
        account=inaccessible_bank, file_format=ImportFileFormat.CSV,
        file_bytes=b"Date,Description,Debit,Credit\n01/06/2026,X,10,\n",
        original_filename="x.csv", imported_by=other_user,
        inline_mapping_data=MAPPING_FORM_FIELDS,
    )

    my_client = authenticated_client(user)
    response = my_client.get("/api/v1/import-batches/")
    assert response.data["count"] == 0


def test_candidate_matches_endpoint_returns_expected_lines():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("25.50"),
        currency="AUD", created_by=user,
    )
    bank_line = entry.lines.get(account=bank)

    client = authenticated_client(user)
    confirm = client.post(
        "/api/v1/import-batches/confirm/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("05/06/2026", "Groceries", "25.50", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    imported_id = ImportedTransaction.objects.get(account=bank).id

    response = client.get(f"/api/v1/imported-transactions/{imported_id}/candidate-matches/")
    assert response.status_code == 200
    assert str(bank_line.id) in [line["id"] for line in response.data]


def test_confirm_match_action_returns_200_and_updates_status():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 5), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("25.50"),
        currency="AUD", created_by=user,
    )
    bank_line = entry.lines.get(account=bank)

    client = authenticated_client(user)
    client.post(
        "/api/v1/import-batches/confirm/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("05/06/2026", "Groceries", "25.50", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    imported_id = ImportedTransaction.objects.get(account=bank).id

    response = client.post(
        f"/api/v1/imported-transactions/{imported_id}/confirm-match/",
        {"journal_line": str(bank_line.id)},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["status"] == "MATCHED"


def test_create_entry_action_returns_400_not_500_on_ledger_error():
    user = make_user()
    entity = make_entity()
    other_entity = Entity.objects.create(name="Other", type=EntityType.BUSINESS)
    make_membership(user, entity, EntityRole.EDITOR)
    bank, _ = make_accounts(entity)
    other_account = Account.objects.create(
        entity=other_entity, account_type=AccountType.EXPENSE, name="Other Expense", native_currency="AUD"
    )

    client = authenticated_client(user)
    client.post(
        "/api/v1/import-batches/confirm/",
        {
            "account": str(bank.id), "file_format": "CSV",
            "file": _csv_file([("05/06/2026", "Groceries", "25.50", "")]), **MAPPING_FORM_FIELDS,
        },
        format="multipart",
    )
    imported_id = ImportedTransaction.objects.get(account=bank).id

    response = client.post(
        f"/api/v1/imported-transactions/{imported_id}/create-entry/",
        {"offsetting_account": str(other_account.id)},
        format="json",
    )
    assert response.status_code == 400


def test_mark_reconciled_endpoint_creates_record_and_clears_lines():
    user = make_user()
    entity = make_entity()
    make_membership(user, entity, EntityRole.EDITOR)
    bank, groceries = make_accounts(entity)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 1), description="Groceries",
        debit_account=groceries, credit_account=bank, amount=Decimal("50"),
        currency="AUD", created_by=user,
    )

    client = authenticated_client(user)
    response = client.post(
        f"/api/v1/accounts/{bank.id}/reconciliation-records/",
        {"statement_date": "2026-06-05", "statement_balance": "950.00"},
        format="json",
    )
    assert response.status_code == 201
    line = entry.lines.get(account=bank)
    line.refresh_from_db()
    assert line.cleared is True


def test_editor_cannot_act_on_imported_transaction_in_inaccessible_entity():
    user = make_user()
    other_user = make_user(email="other@example.com")
    inaccessible_entity = make_entity("Other")
    make_membership(other_user, inaccessible_entity, EntityRole.EDITOR)
    inaccessible_bank, _ = make_accounts(inaccessible_entity)

    confirm_import(
        account=inaccessible_bank, file_format=ImportFileFormat.CSV,
        file_bytes=b"Date,Description,Debit,Credit\n01/06/2026,X,10,\n",
        original_filename="x.csv", imported_by=other_user,
        inline_mapping_data=MAPPING_FORM_FIELDS,
    )
    imported_id = ImportedTransaction.objects.get(account=inaccessible_bank).id

    client = authenticated_client(user)
    response = client.get(f"/api/v1/imported-transactions/{imported_id}/candidate-matches/")
    assert response.status_code == 404
