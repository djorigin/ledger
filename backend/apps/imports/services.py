import hashlib
from dataclasses import dataclass, field, replace
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from apps.imports.exceptions import AlreadyMatchedError, CrossAccountMatchError
from apps.imports.models import (
    ColumnMapping,
    ImportBatch,
    ImportBatchStatus,
    ImportedTransaction,
    ImportedTransactionStatus,
    ImportFileFormat,
)
from apps.imports.parsers.csv_parser import parse_csv, read_csv_headers_and_rows
from apps.imports.parsers.ofx_parser import parse_ofx
from apps.ledger.models import DebitCredit, JournalEntryStatus, JournalLine
from apps.ledger.services import record_simple_transaction

MAPPING_FIELDS = [
    "date_column", "date_format", "description_column", "memo_column",
    "amount_convention", "amount_column", "debit_column", "credit_column",
    "type_column", "type_debit_value", "balance_column", "has_header_row",
]


def _mapping_kwargs(mapping_data) -> dict:
    """Accepts either a ColumnMapping instance or a plain dict of the same
    fields, and returns the kwargs parse_csv() expects."""
    if isinstance(mapping_data, ColumnMapping):
        return {field: getattr(mapping_data, field) for field in MAPPING_FIELDS}
    return {field: mapping_data[field] for field in MAPPING_FIELDS if field in mapping_data}


def compute_csv_external_id(*, account_id, transaction_date, amount, description) -> str:
    """Synthesized dedup key for CSV rows (no native unique id like OFX's
    FITID). Deliberately excludes running_balance -- see services design
    notes: balance display can drift between re-exports of the same range
    without the underlying transaction changing."""
    normalized_description = " ".join(description.strip().lower().split())
    quantized_amount = Decimal(amount).quantize(Decimal("0.0001"))
    payload = f"{account_id}|{transaction_date.isoformat()}|{quantized_amount}|{normalized_description}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_rows(*, file_format, file_bytes, mapping_data=None) -> list:
    if file_format == ImportFileFormat.OFX:
        return parse_ofx(file_bytes)
    kwargs = _mapping_kwargs(mapping_data or {})
    return parse_csv(file_bytes, **kwargs)


@dataclass
class PreviewResult:
    file_format: str
    mapped: bool
    total_row_count: int
    headers: list = field(default_factory=list)
    preview_rows: list = field(default_factory=list)
    available_mappings: list = field(default_factory=list)


def parse_preview(*, account, file_format, file_bytes, column_mapping=None) -> PreviewResult:
    """Read-only: no DB writes. CSV with no mapping returns raw headers +
    unmapped preview rows so the frontend can render the mapping UI; CSV
    with a mapping (or OFX, always) returns ParsedRow-shaped preview rows."""
    if file_format == ImportFileFormat.OFX:
        rows = parse_ofx(file_bytes)
        return PreviewResult(
            file_format=file_format,
            mapped=True,
            total_row_count=len(rows),
            preview_rows=[_row_preview_dict(r) for r in rows[:10]],
        )

    if column_mapping is None:
        headers, raw_rows = read_csv_headers_and_rows(file_bytes)
        return PreviewResult(
            file_format=file_format,
            mapped=False,
            total_row_count=len(raw_rows),
            headers=headers,
            preview_rows=raw_rows,
            available_mappings=list(ColumnMapping.objects.filter(account=account)),
        )

    rows = _parse_rows(file_format=file_format, file_bytes=file_bytes, mapping_data=column_mapping)
    return PreviewResult(
        file_format=file_format,
        mapped=True,
        total_row_count=len(rows),
        preview_rows=[_row_preview_dict(r) for r in rows[:10]],
    )


def _row_preview_dict(row) -> dict:
    return {
        "transaction_date": row.transaction_date.isoformat(),
        "description": row.description,
        "memo": row.memo,
        "amount": str(row.amount),
        "running_balance": str(row.running_balance) if row.running_balance is not None else None,
    }


def confirm_import(
    *,
    account,
    file_format,
    file_bytes,
    original_filename,
    imported_by,
    column_mapping=None,
    inline_mapping_data=None,
    save_mapping_as=None,
):
    """
    Parses the full file, skips rows that already exist for this account
    (by external_id), bulk-creates the rest, and records the ImportBatch.
    Re-importing the same or an overlapping range is always safe: existing
    rows are never re-inserted or re-posted, just silently counted as
    duplicates in the response.
    """
    mapping_for_parsing = column_mapping if column_mapping is not None else inline_mapping_data
    rows = _parse_rows(
        file_format=file_format, file_bytes=file_bytes, mapping_data=mapping_for_parsing
    )

    rows = [
        replace(
            row,
            external_id=compute_csv_external_id(
                account_id=account.id,
                transaction_date=row.transaction_date,
                amount=row.amount,
                description=row.description,
            ),
        )
        if not row.external_id
        else row
        for row in rows
    ]

    existing_external_ids = set(
        ImportedTransaction.objects.filter(
            account=account, external_id__in=[r.external_id for r in rows]
        ).values_list("external_id", flat=True)
    )
    new_rows = [r for r in rows if r.external_id not in existing_external_ids]
    duplicate_count = len(rows) - len(new_rows)

    with transaction.atomic():
        saved_mapping = None
        if file_format == ImportFileFormat.CSV and save_mapping_as:
            mapping_kwargs = _mapping_kwargs(inline_mapping_data or {})
            saved_mapping = ColumnMapping.objects.create(
                account=account, name=save_mapping_as, created_by=imported_by, **mapping_kwargs
            )
            saved_mapping.full_clean()
        elif column_mapping is not None:
            saved_mapping = column_mapping

        dates = [r.transaction_date for r in rows] if rows else []
        batch = ImportBatch.objects.create(
            account=account,
            file_format=file_format,
            original_filename=original_filename,
            column_mapping=saved_mapping,
            status=ImportBatchStatus.IMPORTED,
            statement_start_date=min(dates) if dates else None,
            statement_end_date=max(dates) if dates else None,
            row_count=len(new_rows),
            duplicate_count=duplicate_count,
            imported_by=imported_by,
            confirmed_at=timezone.now(),
        )

        ImportedTransaction.objects.bulk_create(
            ImportedTransaction(
                import_batch=batch,
                account=account,
                transaction_date=r.transaction_date,
                description=r.description,
                memo=r.memo,
                amount=r.amount,
                running_balance=r.running_balance,
                external_id=r.external_id,
                raw_row=r.raw_row,
            )
            for r in new_rows
        )

    return batch


def find_candidate_matches(imported_transaction, *, date_window_days=3):
    """
    Returns existing, unreconciled JournalLines on the same account that
    are plausible matches for this ImportedTransaction, ordered best-first
    (exact date first, then by closest date). Never auto-matches -- a
    human always confirms. Bounded false-positive risk: account, exact
    amount, and date window must all agree.
    """
    account = imported_transaction.account
    window_start = imported_transaction.transaction_date - timedelta(days=date_window_days)
    window_end = imported_transaction.transaction_date + timedelta(days=date_window_days)

    is_increase = imported_transaction.amount > 0
    debit_side = is_increase if account.normal_balance == DebitCredit.DEBIT else not is_increase
    amount_abs = abs(imported_transaction.amount)

    qs = JournalLine.objects.filter(
        account=account,
        journal_entry__status=JournalEntryStatus.POSTED,
        journal_entry__entry_date__range=(window_start, window_end),
        cleared=False,
    ).exclude(matched_imports__isnull=False)

    qs = qs.filter(debit_amount=amount_abs) if debit_side else qs.filter(credit_amount=amount_abs)

    target_date = imported_transaction.transaction_date
    return qs.annotate(
        is_exact_date=Case(
            When(journal_entry__entry_date=target_date, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("is_exact_date", "journal_entry__entry_date")


def confirm_match(*, imported_transaction, journal_line, matched_by):
    if imported_transaction.status != ImportedTransactionStatus.UNMATCHED:
        raise AlreadyMatchedError(
            f"Imported transaction is already {imported_transaction.status}."
        )
    if journal_line.account_id != imported_transaction.account_id:
        raise CrossAccountMatchError(
            "Cannot match a journal line on a different account than the imported transaction."
        )
    if journal_line.matched_imports.exists():
        raise AlreadyMatchedError("This journal line is already matched to another import row.")

    imported_transaction.matched_line = journal_line
    imported_transaction.status = ImportedTransactionStatus.MATCHED
    imported_transaction.matched_by = matched_by
    imported_transaction.matched_at = timezone.now()
    imported_transaction.save(
        update_fields=["matched_line", "status", "matched_by", "matched_at"]
    )
    return imported_transaction


def create_entry_from_import(*, imported_transaction, offsetting_account, created_by, description=None):
    """
    Builds a 2-line entry from the imported row and posts it through
    record_simple_transaction -- never a hand-rolled insert, so the same
    balance/currency validation and audit trail apply as any other entry.
    """
    if imported_transaction.status != ImportedTransactionStatus.UNMATCHED:
        raise AlreadyMatchedError(
            f"Imported transaction is already {imported_transaction.status}."
        )

    account = imported_transaction.account
    amount_abs = abs(imported_transaction.amount)
    is_increase = imported_transaction.amount > 0
    debit_side = is_increase if account.normal_balance == DebitCredit.DEBIT else not is_increase

    debit_account = account if debit_side else offsetting_account
    credit_account = offsetting_account if debit_side else account

    entry = record_simple_transaction(
        entity=account.entity,
        entry_date=imported_transaction.transaction_date,
        description=description or imported_transaction.description,
        debit_account=debit_account,
        credit_account=credit_account,
        amount=amount_abs,
        currency=account.native_currency,
        created_by=created_by,
    )

    imported_transaction.created_entry = entry
    imported_transaction.status = ImportedTransactionStatus.POSTED
    imported_transaction.matched_by = created_by
    imported_transaction.matched_at = timezone.now()
    imported_transaction.save(
        update_fields=["created_entry", "status", "matched_by", "matched_at"]
    )
    return imported_transaction


def ignore_imported_transaction(*, imported_transaction):
    if imported_transaction.status != ImportedTransactionStatus.UNMATCHED:
        raise AlreadyMatchedError(
            f"Imported transaction is already {imported_transaction.status}."
        )
    imported_transaction.status = ImportedTransactionStatus.IGNORED
    imported_transaction.save(update_fields=["status"])
    return imported_transaction
