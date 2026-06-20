from datetime import date
from decimal import Decimal

import pytest

from apps.imports.models import ImportedTransaction
from apps.imports.services import find_candidate_matches
from apps.imports.tests.helpers import make_account, make_entity, make_import_batch, make_user
from apps.ledger.models import AccountType
from apps.ledger.services import record_simple_transaction

pytestmark = pytest.mark.django_db

_counter = iter(range(1_000_000))


def _make_imported(account, user, *, transaction_date, amount, matched_line=None):
    batch = make_import_batch(account, user)
    return ImportedTransaction.objects.create(
        import_batch=batch,
        account=account,
        transaction_date=transaction_date,
        description="Groceries",
        amount=amount,
        external_id=f"test-external-id-{next(_counter)}",
        matched_line=matched_line,
    )


def _post_entry(entity, user, bank, expense, *, entry_date, amount=Decimal("25.50")):
    return record_simple_transaction(
        entity=entity, entry_date=entry_date, description="Groceries",
        debit_account=expense, credit_account=bank,
        amount=amount, currency="AUD", created_by=user,
    )


def test_find_candidate_matches_exact_date_and_amount():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))

    imported = _make_imported(
        bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-25.50")
    )
    candidates = find_candidate_matches(imported)
    bank_line = entry.lines.get(account=bank)
    assert bank_line in candidates


def test_find_candidate_matches_within_date_window():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))
    bank_line = entry.lines.get(account=bank)

    for offset, should_match in [(1, True), (2, True), (3, True), (4, False)]:
        imported = _make_imported(
            bank, user, transaction_date=date(2026, 6, 5 + offset), amount=Decimal("-25.50")
        )
        candidates = find_candidate_matches(imported)
        assert (bank_line in candidates) == should_match, f"offset={offset}"


def test_find_candidate_matches_excludes_different_account():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    other_bank = make_account(entity, name="Other Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))

    imported = _make_imported(
        other_bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-25.50")
    )
    assert find_candidate_matches(imported).count() == 0


def test_find_candidate_matches_excludes_different_amount():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))

    imported = _make_imported(
        bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-99.99")
    )
    assert find_candidate_matches(imported).count() == 0


def test_find_candidate_matches_excludes_already_matched_lines():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))
    bank_line = entry.lines.get(account=bank)

    _make_imported(
        bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-25.50"),
        matched_line=bank_line,
    )
    new_imported = _make_imported(
        bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-25.50")
    )
    assert bank_line not in find_candidate_matches(new_imported)


def test_find_candidate_matches_excludes_cleared_lines():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))
    bank_line = entry.lines.get(account=bank)
    bank_line.cleared = True
    bank_line.save(update_fields=["cleared"])

    imported = _make_imported(
        bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-25.50")
    )
    assert bank_line not in find_candidate_matches(imported)


def test_find_candidate_matches_excludes_draft_and_reversed_entries():
    from apps.ledger.services import reverse_journal_entry

    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry = _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))
    bank_line_id = entry.lines.get(account=bank).id
    reverse_journal_entry(entry=entry, reversed_by_user=user)

    imported = _make_imported(
        bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-25.50")
    )
    candidate_ids = [line.id for line in find_candidate_matches(imported)]
    assert bank_line_id not in candidate_ids


def test_find_candidate_matches_orders_by_date_proximity():
    entity = make_entity()
    user = make_user()
    bank = make_account(entity, name="Bank")
    expense = make_account(entity, name="Groceries", account_type=AccountType.EXPENSE)
    entry_far = _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 3))
    entry_close = _post_entry(entity, user, bank, expense, entry_date=date(2026, 6, 5))

    imported = _make_imported(
        bank, user, transaction_date=date(2026, 6, 5), amount=Decimal("-25.50")
    )
    candidates = list(find_candidate_matches(imported))
    close_line = entry_close.lines.get(account=bank)
    far_line = entry_far.lines.get(account=bank)
    assert candidates.index(close_line) < candidates.index(far_line)
