from datetime import date
from decimal import Decimal

from apps.imports.parsers.ofx_parser import parse_ofx

SAMPLE_OFX = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20260620120000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>AUD
<BANKACCTFROM>
<BANKID>062000
<ACCTID>12345678
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260601
<DTEND>20260620
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260605
<TRNAMT>-25.50
<FITID>FIT001
<NAME>Groceries Store
<MEMO>Weekly shop
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260610
<TRNAMT>1500.00
<FITID>FIT002
<NAME>Salary
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>2000.00
<DTASOF>20260620
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


def test_parses_basic_ofx_statement():
    rows = parse_ofx(SAMPLE_OFX)
    assert len(rows) == 2
    assert rows[0].transaction_date == date(2026, 6, 5)
    assert rows[0].description == "Groceries Store"
    assert rows[0].memo == "Weekly shop"


def test_ofx_signed_amount_matches_normalized_convention():
    rows = parse_ofx(SAMPLE_OFX)
    assert rows[0].amount == Decimal("-25.50")  # debit/withdrawal -> negative
    assert rows[1].amount == Decimal("1500.00")  # credit/deposit -> positive
    assert isinstance(rows[0].amount, Decimal)


def test_ofx_fitid_used_as_external_id():
    rows = parse_ofx(SAMPLE_OFX)
    assert rows[0].external_id == "FIT001"
    assert rows[1].external_id == "FIT002"


def test_ofx_running_balance_is_none():
    rows = parse_ofx(SAMPLE_OFX)
    assert all(row.running_balance is None for row in rows)
