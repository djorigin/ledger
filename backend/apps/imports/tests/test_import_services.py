from datetime import date
from decimal import Decimal

import pytest

from apps.entities.models import Entity, EntityType
from apps.imports.exceptions import AlreadyMatchedError, CrossAccountMatchError
from apps.imports.models import ColumnMapping, ImportedTransaction, ImportedTransactionStatus, ImportFileFormat
from apps.imports.services import confirm_import, confirm_match, create_entry_from_import
from apps.imports.tests.helpers import make_account, make_entity, make_user
from apps.ledger.exceptions import LedgerError
from apps.ledger.models import AccountType, JournalEntryStatus
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db

CSV_MAPPING = dict(
    date_column="Date", date_format="%d/%m/%Y",
    description_column="Description", amount_convention="DEBIT_CREDIT",
    debit_column="Debit", credit_column="Credit",
)


def _csv(rows):
    header = "Date,Description,Debit,Credit\n"
    body = "".join(f"{d},{desc},{debit},{credit}\n" for d, desc, debit, credit in rows)
    return (header + body).encode()


def test_confirm_import_creates_batch_and_transactions_csv():
    entity = make_entity()
    user = make_user()
    account = make_account(entity)
    data = _csv([("01/06/2026", "Groceries", "25.50", ""), ("02/06/2026", "Salary", "", "1500.00")])

    batch = confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    assert batch.row_count == 2
    assert batch.transactions.count() == 2


def test_confirm_import_creates_batch_and_transactions_ofx():
    entity = make_entity()
    user = make_user()
    account = make_account(entity)
    ofx_bytes = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX><SIGNONMSGSRSV1><SONRS><STATUS><CODE>0
<SEVERITY>INFO
</STATUS><DTSERVER>20260620120000
<LANGUAGE>ENG
</SONRS></SIGNONMSGSRSV1><BANKMSGSRSV1><STMTTRNRS><TRNUID>1
<STATUS><CODE>0
<SEVERITY>INFO
</STATUS><STMTRS><CURDEF>AUD
<BANKACCTFROM><BANKID>062000
<ACCTID>12345678
<ACCTTYPE>CHECKING
</BANKACCTFROM><BANKTRANLIST><DTSTART>20260601
<DTEND>20260620
<STMTTRN><TRNTYPE>DEBIT
<DTPOSTED>20260605
<TRNAMT>-25.50
<FITID>FIT001
<NAME>Groceries
</STMTTRN></BANKTRANLIST><LEDGERBAL><BALAMT>2000.00
<DTASOF>20260620
</LEDGERBAL></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""
    batch = confirm_import(
        account=account, file_format=ImportFileFormat.OFX, file_bytes=ofx_bytes,
        original_filename="a.ofx", imported_by=user,
    )
    assert batch.row_count == 1


def test_confirm_import_persists_mapping_when_save_mapping_as_given():
    entity = make_entity()
    user = make_user()
    account = make_account(entity)
    data = _csv([("01/06/2026", "Groceries", "25.50", "")])

    confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
        save_mapping_as="My Bank CSV",
    )
    assert ColumnMapping.objects.filter(account=account, name="My Bank CSV").exists()


def test_confirm_import_reuses_existing_mapping_by_id():
    entity = make_entity()
    user = make_user()
    account = make_account(entity)
    mapping = ColumnMapping.objects.create(
        account=account, name="My Bank CSV", created_by=user, **CSV_MAPPING
    )
    data = _csv([("01/06/2026", "Groceries", "25.50", "")])

    confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, column_mapping=mapping,
    )
    assert ColumnMapping.objects.filter(account=account).count() == 1


def test_confirm_match_links_existing_journal_line_and_sets_matched_status():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 5), description="Groceries",
        debit_account=expense, credit_account=bank, amount=Decimal("25.50"),
        currency="AUD", created_by=user,
    )
    bank_line = entry.lines.get(account=bank)

    data = _csv([("05/06/2026", "Groceries", "25.50", "")])
    batch = confirm_import(
        account=bank, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    imported = batch.transactions.get()

    confirm_match(imported_transaction=imported, journal_line=bank_line, matched_by=user)
    imported.refresh_from_db()
    assert imported.status == ImportedTransactionStatus.MATCHED
    assert imported.matched_line == bank_line


def test_confirm_match_rejects_already_matched_line():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 5), description="Groceries",
        debit_account=expense, credit_account=bank, amount=Decimal("25.50"),
        currency="AUD", created_by=user,
    )
    bank_line = entry.lines.get(account=bank)
    data = _csv([
        ("05/06/2026", "Groceries 1", "25.50", ""),
        ("05/06/2026", "Groceries 2", "25.50", ""),
    ])
    batch = confirm_import(
        account=bank, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    first, second = batch.transactions.order_by("description")

    confirm_match(imported_transaction=first, journal_line=bank_line, matched_by=user)
    with pytest.raises(AlreadyMatchedError):
        confirm_match(imported_transaction=second, journal_line=bank_line, matched_by=user)


def test_confirm_match_rejects_cross_account_line():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    other_bank = make_account(entity, name="Other Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = record_simple_transaction(
        entity=entity, entry_date=date(2026, 6, 5), description="Groceries",
        debit_account=expense, credit_account=bank, amount=Decimal("25.50"),
        currency="AUD", created_by=user,
    )
    bank_line = entry.lines.get(account=bank)
    data = _csv([("05/06/2026", "Groceries", "25.50", "")])
    batch = confirm_import(
        account=other_bank, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    imported = batch.transactions.get()

    with pytest.raises(CrossAccountMatchError):
        confirm_match(imported_transaction=imported, journal_line=bank_line, matched_by=user)


def test_create_entry_from_import_calls_post_journal_entry_not_a_bypass():
    entity = make_entity()
    other_entity = Entity.objects.create(name="Other", type=EntityType.BUSINESS)
    user = make_user()
    bank = make_account(entity, name="Bank")
    other_entity_account = make_account(other_entity, name="Other Entity Account")

    data = _csv([("05/06/2026", "Groceries", "25.50", "")])
    batch = confirm_import(
        account=bank, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    imported = batch.transactions.get()

    # An offsetting account from a different entity must be rejected by
    # post_journal_entry's real CrossEntityAccountError -- proves this
    # path goes through actual validation, not a hand-rolled insert.
    with pytest.raises(LedgerError):
        create_entry_from_import(
            imported_transaction=imported, offsetting_account=other_entity_account,
            created_by=user,
        )
    imported.refresh_from_db()
    assert imported.status == ImportedTransactionStatus.UNMATCHED


def test_create_entry_from_import_sets_correct_debit_credit_sides():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)

    data = _csv([("05/06/2026", "Groceries", "25.50", "")])  # withdrawal, negative amount
    batch = confirm_import(
        account=bank, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    imported = batch.transactions.get()

    create_entry_from_import(
        imported_transaction=imported, offsetting_account=expense, created_by=user,
    )
    imported.refresh_from_db()
    entry = imported.created_entry
    bank_line = entry.lines.get(account=bank)
    expense_line = entry.lines.get(account=expense)
    assert bank_line.credit_amount == Decimal("25.5000")
    assert expense_line.debit_amount == Decimal("25.5000")


def test_create_entry_from_import_marks_transaction_posted_and_links_entry():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)

    data = _csv([("05/06/2026", "Groceries", "25.50", "")])
    batch = confirm_import(
        account=bank, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    imported = batch.transactions.get()

    create_entry_from_import(
        imported_transaction=imported, offsetting_account=expense, created_by=user,
    )
    imported.refresh_from_db()
    assert imported.status == ImportedTransactionStatus.POSTED
    assert imported.created_entry is not None
    assert imported.created_entry.status == JournalEntryStatus.POSTED
