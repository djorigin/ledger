import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from apps.imports.exceptions import ColumnMappingError
from apps.imports.parsers import ParsedRow


def _rows_as_dicts(file_bytes: bytes, *, has_header_row: bool) -> tuple[list[str], list[dict]]:
    text = file_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if row]
    if not rows:
        return [], []

    if has_header_row:
        headers = rows[0]
        data_rows = rows[1:]
    else:
        headers = [f"Column {i + 1}" for i in range(len(rows[0]))]
        data_rows = rows

    dict_rows = [dict(zip(headers, row)) for row in data_rows]
    return headers, dict_rows


def read_csv_headers_and_rows(
    file_bytes: bytes, *, has_header_row: bool = True, limit: int = 10
) -> tuple[list[str], list[dict]]:
    """Headers + first `limit` raw rows, for the column-mapping UI before a
    mapping has been chosen. No interpretation of the data happens here."""
    headers, dict_rows = _rows_as_dicts(file_bytes, has_header_row=has_header_row)
    return headers, dict_rows[:limit]


def _parse_decimal(raw_value: str, *, field_name: str) -> Decimal:
    cleaned = raw_value.strip().replace(",", "").replace("$", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ColumnMappingError(f"Could not parse {field_name} value: {raw_value!r}") from exc


def _row_amount(row: dict, *, amount_convention, amount_column, debit_column,
                 credit_column, type_column, type_debit_value) -> Decimal:
    if amount_convention == "SIGNED_AMOUNT":
        return _parse_decimal(row.get(amount_column, ""), field_name="amount")

    if type_column:
        # One unsigned amount column + a separate Debit/Credit type indicator.
        raw_amount = abs(_parse_decimal(row.get(amount_column, ""), field_name="amount"))
        is_debit = row.get(type_column, "").strip().lower() == type_debit_value.strip().lower()
        return -raw_amount if is_debit else raw_amount

    debit_raw = row.get(debit_column, "").strip() if debit_column else ""
    credit_raw = row.get(credit_column, "").strip() if credit_column else ""
    debit_value = _parse_decimal(debit_raw, field_name="debit") if debit_raw else Decimal("0")
    credit_value = _parse_decimal(credit_raw, field_name="credit") if credit_raw else Decimal("0")
    # A withdrawal (debit, in the bank's own statement language) decreases
    # the account balance -> negative in our normalized signed convention.
    return credit_value - debit_value


def parse_csv(
    file_bytes: bytes,
    *,
    date_column: str,
    date_format: str,
    description_column: str,
    amount_convention: str,
    memo_column: str = "",
    amount_column: str = "",
    debit_column: str = "",
    credit_column: str = "",
    type_column: str = "",
    type_debit_value: str = "",
    balance_column: str = "",
    has_header_row: bool = True,
) -> list[ParsedRow]:
    headers, dict_rows = _rows_as_dicts(file_bytes, has_header_row=has_header_row)

    for required in (date_column, description_column):
        if required not in headers:
            raise ColumnMappingError(f"Column {required!r} not found in file headers {headers!r}.")

    parsed_rows = []
    for row in dict_rows:
        raw_date = row.get(date_column, "").strip()
        try:
            transaction_date = datetime.strptime(raw_date, date_format).date()
        except ValueError as exc:
            raise ColumnMappingError(
                f"Could not parse date {raw_date!r} using format {date_format!r}."
            ) from exc

        amount = _row_amount(
            row,
            amount_convention=amount_convention,
            amount_column=amount_column,
            debit_column=debit_column,
            credit_column=credit_column,
            type_column=type_column,
            type_debit_value=type_debit_value,
        )

        running_balance = None
        if balance_column and row.get(balance_column, "").strip():
            running_balance = _parse_decimal(row[balance_column], field_name="balance")

        description = " ".join(row.get(description_column, "").strip().split())

        parsed_rows.append(
            ParsedRow(
                transaction_date=transaction_date,
                description=description,
                amount=amount,
                memo=row.get(memo_column, "").strip() if memo_column else "",
                running_balance=running_balance,
                raw_row=dict(row),
            )
        )
    return parsed_rows
