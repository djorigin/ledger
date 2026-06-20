from datetime import date
from decimal import Decimal

import pytest

from apps.imports.exceptions import ColumnMappingError
from apps.imports.parsers.csv_parser import parse_csv, read_csv_headers_and_rows


def test_parses_signed_amount_column_csv():
    data = b"Date,Description,Amount\n01/06/2026,Groceries,-25.50\n02/06/2026,Salary,1500.00\n"
    rows = parse_csv(
        data,
        date_column="Date", date_format="%d/%m/%Y",
        description_column="Description", amount_convention="SIGNED_AMOUNT",
        amount_column="Amount",
    )
    assert len(rows) == 2
    assert rows[0].transaction_date == date(2026, 6, 1)
    assert rows[0].amount == Decimal("-25.50")
    assert rows[1].amount == Decimal("1500.00")


def test_parses_debit_credit_column_csv():
    data = b"Date,Description,Debit,Credit\n01/06/2026,Groceries,25.50,\n02/06/2026,Salary,,1500.00\n"
    rows = parse_csv(
        data,
        date_column="Date", date_format="%d/%m/%Y",
        description_column="Description", amount_convention="DEBIT_CREDIT",
        debit_column="Debit", credit_column="Credit",
    )
    assert rows[0].amount == Decimal("-25.50")
    assert rows[1].amount == Decimal("1500.00")


def test_parses_type_column_with_unsigned_amount_csv():
    data = (
        b"Date,Description,Amount,Type\n"
        b"01/06/2026,Groceries,25.50,Debit\n"
        b"02/06/2026,Salary,1500.00,Credit\n"
    )
    rows = parse_csv(
        data,
        date_column="Date", date_format="%d/%m/%Y",
        description_column="Description", amount_convention="DEBIT_CREDIT",
        amount_column="Amount", type_column="Type", type_debit_value="Debit",
    )
    assert rows[0].amount == Decimal("-25.50")
    assert rows[1].amount == Decimal("1500.00")


@pytest.mark.parametrize(
    "date_format,raw_date",
    [("%d/%m/%Y", "25/12/2026"), ("%m/%d/%Y", "12/25/2026"), ("%Y-%m-%d", "2026-12-25")],
)
def test_parses_various_date_formats(date_format, raw_date):
    data = f"Date,Description,Amount\n{raw_date},Christmas,-10.00\n".encode()
    rows = parse_csv(
        data,
        date_column="Date", date_format=date_format,
        description_column="Description", amount_convention="SIGNED_AMOUNT",
        amount_column="Amount",
    )
    assert rows[0].transaction_date == date(2026, 12, 25)


def test_parses_optional_balance_column():
    data = b"Date,Description,Amount,Balance\n01/06/2026,Groceries,-25.50,100.00\n"
    rows = parse_csv(
        data,
        date_column="Date", date_format="%d/%m/%Y",
        description_column="Description", amount_convention="SIGNED_AMOUNT",
        amount_column="Amount", balance_column="Balance",
    )
    assert rows[0].running_balance == Decimal("100.00")

    data_no_balance = b"Date,Description,Amount\n01/06/2026,Groceries,-25.50\n"
    rows_no_balance = parse_csv(
        data_no_balance,
        date_column="Date", date_format="%d/%m/%Y",
        description_column="Description", amount_convention="SIGNED_AMOUNT",
        amount_column="Amount",
    )
    assert rows_no_balance[0].running_balance is None


def test_handles_no_header_row():
    data = b"01/06/2026,Groceries,-25.50\n"
    headers, preview = read_csv_headers_and_rows(data, has_header_row=False)
    assert headers == ["Column 1", "Column 2", "Column 3"]
    rows = parse_csv(
        data,
        date_column="Column 1", date_format="%d/%m/%Y",
        description_column="Column 2", amount_convention="SIGNED_AMOUNT",
        amount_column="Column 3", has_header_row=False,
    )
    assert rows[0].amount == Decimal("-25.50")


def test_raises_on_missing_required_column():
    data = b"Date,Description,Amount\n01/06/2026,Groceries,-25.50\n"
    with pytest.raises(ColumnMappingError):
        parse_csv(
            data,
            date_column="NotAColumn", date_format="%d/%m/%Y",
            description_column="Description", amount_convention="SIGNED_AMOUNT",
            amount_column="Amount",
        )


def test_normalizes_description_whitespace_for_hashing():
    data = b"Date,Description,Amount\n01/06/2026,  Groceries   Store  ,-25.50\n"
    rows = parse_csv(
        data,
        date_column="Date", date_format="%d/%m/%Y",
        description_column="Description", amount_convention="SIGNED_AMOUNT",
        amount_column="Amount",
    )
    assert rows[0].description == "Groceries Store"
