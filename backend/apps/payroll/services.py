from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from apps.ledger.services import JournalLineInput, post_journal_entry, reverse_journal_entry
from apps.payroll.models import Payslip


def _build_lines(payslip: Payslip) -> list[JournalLineInput]:
    """
    Six possible debit lines (skip any that are zero -- e.g. a fortnight
    with no CFMEU/social-club deduction) plus one credit line, in
    *payslip.currency*. Debits always sum to gross_amount by construction
    (deductions + net_pay = gross_amount, per Payslip.expected_net_pay),
    matching the single credit to income_account -- balances without
    needing the "PAYG tax as a liability credit" treatment the original
    spec used, which didn't balance (see plan notes).
    """
    candidates = [
        (payslip.pretax_lease_expense_account, payslip.deduction_pretax_lease),
        (payslip.tax_expense_account, payslip.deduction_tax),
        (payslip.fuel_card_expense_account, payslip.deduction_fuel_card),
        (payslip.social_club_expense_account, payslip.deduction_social_club),
        (payslip.cfmeu_expense_account, payslip.deduction_cfmeu),
        (payslip.bank_account, payslip.net_pay),
    ]
    lines = [
        JournalLineInput(account=account, currency=payslip.currency, debit_amount=amount)
        for account, amount in candidates
        if amount and amount > 0
    ]
    lines.append(
        JournalLineInput(
            account=payslip.income_account, currency=payslip.currency, credit_amount=payslip.gross_amount
        )
    )
    return lines


def record_payslip(*, created_by, **fields) -> Payslip:
    payslip = Payslip(created_by=created_by, **fields)
    payslip.full_clean()

    with transaction.atomic():
        entry = post_journal_entry(
            entity=payslip.entity,
            entry_date=payslip.payment_date,
            description=f"Payslip {payslip.pay_period_start}..{payslip.pay_period_end}",
            created_by=created_by,
            lines=_build_lines(payslip),
        )
        payslip.journal_entry = entry
        payslip.save()
    return payslip


def update_payslip(*, payslip: Payslip, updated_by, **fields) -> Payslip:
    """
    Recomputes/validates net_pay exactly like record_payslip. If a journal
    entry already exists, reverses it (via the existing
    reverse_journal_entry, never editing a posted entry in place) and
    posts a fresh one with the updated amounts -- the same correction
    pattern Bill/Invoice use via cancel_bill/cancel_invoice.
    """
    for field_name, value in fields.items():
        setattr(payslip, field_name, value)
    payslip.full_clean()

    with transaction.atomic():
        if payslip.journal_entry_id is not None:
            reverse_journal_entry(entry=payslip.journal_entry, reversed_by_user=updated_by)
        entry = post_journal_entry(
            entity=payslip.entity,
            entry_date=payslip.payment_date,
            description=f"Payslip {payslip.pay_period_start}..{payslip.pay_period_end} (corrected)",
            created_by=updated_by,
            lines=_build_lines(payslip),
        )
        payslip.journal_entry = entry
        payslip.save()
    return payslip


@dataclass(frozen=True)
class PayslipSummary:
    gross: Decimal
    tax: Decimal
    net: Decimal
    count: int


def compute_payslip_summary(payslips) -> PayslipSummary:
    totals = payslips.aggregate(
        gross=Coalesce(Sum("gross_amount"), Decimal("0")),
        tax=Coalesce(Sum("deduction_tax"), Decimal("0")),
        net=Coalesce(Sum("net_pay"), Decimal("0")),
    )
    return PayslipSummary(
        gross=totals["gross"], tax=totals["tax"], net=totals["net"], count=payslips.count()
    )
