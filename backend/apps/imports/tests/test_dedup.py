import pytest

from apps.imports.models import ImportedTransaction, ImportFileFormat
from apps.imports.services import confirm_import, create_entry_from_import
from apps.imports.tests.helpers import make_account, make_entity, make_user
from apps.ledger.models import AccountType
from apps.ledger.models import JournalEntry

pytestmark = pytest.mark.django_db

CSV_MAPPING = dict(
    date_column="Date", date_format="%d/%m/%Y",
    description_column="Description", amount_convention="SIGNED_AMOUNT",
    amount_column="Amount",
)


def _csv(rows):
    header = "Date,Description,Amount\n"
    body = "".join(f"{d},{desc},{amt}\n" for d, desc, amt in rows)
    return (header + body).encode()


def test_reimporting_identical_csv_skips_all_rows_second_time():
    entity = make_entity()
    user = make_user()
    account = make_account(entity)
    data = _csv([("01/06/2026", "Groceries", "-25.50"), ("02/06/2026", "Salary", "1500.00")])

    confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    assert ImportedTransaction.objects.count() == 2

    second = confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    assert ImportedTransaction.objects.count() == 2
    assert second.row_count == 0
    assert second.duplicate_count == 2


def test_reimporting_overlapping_date_range_csv_skips_only_overlap():
    entity = make_entity()
    user = make_user()
    account = make_account(entity)
    first = _csv([
        ("01/06/2026", "Groceries", "-25.50"),
        ("05/06/2026", "Cafe", "-10.00"),
    ])
    second = _csv([
        ("05/06/2026", "Cafe", "-10.00"),
        ("10/06/2026", "Salary", "1500.00"),
    ])

    confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=first,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    batch2 = confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=second,
        original_filename="b.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    assert ImportedTransaction.objects.count() == 3
    assert batch2.row_count == 1
    assert batch2.duplicate_count == 1


def test_ofx_fitid_dedup_prevents_duplicate_rows():
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
<NAME>Groceries Store
</STMTTRN></BANKTRANLIST><LEDGERBAL><BALAMT>2000.00
<DTASOF>20260620
</LEDGERBAL></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""
    confirm_import(
        account=account, file_format=ImportFileFormat.OFX, file_bytes=ofx_bytes,
        original_filename="a.ofx", imported_by=user,
    )
    second = confirm_import(
        account=account, file_format=ImportFileFormat.OFX, file_bytes=ofx_bytes,
        original_filename="a.ofx", imported_by=user,
    )
    assert ImportedTransaction.objects.count() == 1
    assert second.duplicate_count == 1


def test_same_amount_date_description_different_accounts_not_deduped():
    entity = make_entity()
    user = make_user()
    account_a = make_account(entity, name="Bank A")
    account_b = make_account(entity, name="Bank B")
    data = _csv([("01/06/2026", "Groceries", "-25.50")])

    confirm_import(
        account=account_a, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    confirm_import(
        account=account_b, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    assert ImportedTransaction.objects.filter(account=account_a).count() == 1
    assert ImportedTransaction.objects.filter(account=account_b).count() == 1


def test_duplicate_detection_never_double_posts():
    entity = make_entity()
    user = make_user()
    account = make_account(entity)
    expense_account = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    data = _csv([("01/06/2026", "Groceries", "-25.50")])

    confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    imported = ImportedTransaction.objects.get()
    create_entry_from_import(
        imported_transaction=imported, offsetting_account=expense_account, created_by=user,
    )
    assert JournalEntry.objects.count() == 1

    confirm_import(
        account=account, file_format=ImportFileFormat.CSV, file_bytes=data,
        original_filename="a-reexport.csv", imported_by=user, inline_mapping_data=CSV_MAPPING,
    )
    assert ImportedTransaction.objects.count() == 1
    assert JournalEntry.objects.count() == 1
