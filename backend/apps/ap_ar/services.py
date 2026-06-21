from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.ap_ar.exceptions import AlreadyCancelledError, HasPaymentsError, OverpaymentError
from apps.ap_ar.models import Bill, BillPayment, Invoice, InvoicePayment
from apps.ledger.services import JournalLineInput, post_journal_entry, reverse_journal_entry


def record_bill(
    *,
    entity,
    vendor_name,
    description,
    bill_date,
    due_date,
    amount,
    currency,
    expense_account,
    payable_account,
    created_by,
) -> Bill:
    """
    The liability exists the moment the bill is received, whether or not
    it's been paid -- posts Dr expense_account, Cr payable_account
    immediately via the one sanctioned write path (post_journal_entry).
    """
    with transaction.atomic():
        entry = post_journal_entry(
            entity=entity,
            entry_date=bill_date,
            description=f"Bill: {vendor_name} - {description}" if description else f"Bill: {vendor_name}",
            created_by=created_by,
            lines=[
                JournalLineInput(account=expense_account, currency=currency, debit_amount=amount),
                JournalLineInput(account=payable_account, currency=currency, credit_amount=amount),
            ],
        )
        bill = Bill(
            entity=entity,
            vendor_name=vendor_name,
            description=description,
            bill_date=bill_date,
            due_date=due_date,
            amount=amount,
            currency=currency,
            expense_account=expense_account,
            payable_account=payable_account,
            journal_entry=entry,
            created_by=created_by,
        )
        bill.full_clean()
        bill.save()
    return bill


@dataclass(frozen=True)
class BillProgress:
    bill: Bill
    amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    status: str
    is_overdue: bool


def compute_bill_progress(bill: Bill, *, as_of: date | None = None) -> BillProgress:
    """Status and amount_paid are computed from BillPayment rows, never
    stored -- same "derive, don't duplicate" principle as BudgetProgress/
    ProjectProgress elsewhere in this codebase."""
    today = as_of or timezone.now().date()
    amount_paid = bill.payments.aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]
    amount_due = bill.amount - amount_paid

    if bill.is_cancelled:
        status = "CANCELLED"
    elif amount_paid <= 0:
        status = "OPEN"
    elif amount_due > 0:
        status = "PARTIALLY_PAID"
    else:
        status = "PAID"

    is_overdue = status in ("OPEN", "PARTIALLY_PAID") and bill.due_date < today

    return BillProgress(
        bill=bill,
        amount=bill.amount,
        amount_paid=amount_paid,
        amount_due=amount_due,
        status=status,
        is_overdue=is_overdue,
    )


def record_bill_payment(*, bill, payment_date, amount, payment_account, created_by) -> BillPayment:
    if bill.is_cancelled:
        raise AlreadyCancelledError("Cannot record a payment against a cancelled bill.")
    progress = compute_bill_progress(bill)
    if amount > progress.amount_due:
        raise OverpaymentError(
            f"Payment of {amount} exceeds the remaining amount due of {progress.amount_due}."
        )

    with transaction.atomic():
        entry = post_journal_entry(
            entity=bill.entity,
            entry_date=payment_date,
            description=f"Payment: {bill.vendor_name}",
            created_by=created_by,
            lines=[
                JournalLineInput(
                    account=bill.payable_account, currency=bill.currency, debit_amount=amount
                ),
                JournalLineInput(
                    account=payment_account, currency=bill.currency, credit_amount=amount
                ),
            ],
        )
        payment = BillPayment(
            bill=bill,
            payment_date=payment_date,
            amount=amount,
            payment_account=payment_account,
            journal_entry=entry,
            created_by=created_by,
        )
        payment.full_clean()
        payment.save()
    return payment


def cancel_bill(*, bill, cancelled_by) -> Bill:
    if bill.is_cancelled:
        raise AlreadyCancelledError(f"Bill '{bill}' is already cancelled.")
    if bill.payments.exists():
        raise HasPaymentsError(
            "Cannot cancel a bill with recorded payments. Record an offsetting bill instead."
        )
    with transaction.atomic():
        reverse_journal_entry(entry=bill.journal_entry, reversed_by_user=cancelled_by)
        bill.is_cancelled = True
        bill.save(update_fields=["is_cancelled", "updated_at"])
    return bill


def record_invoice(
    *,
    entity,
    customer_name,
    description,
    invoice_date,
    due_date,
    amount,
    currency,
    income_account,
    receivable_account,
    created_by,
) -> Invoice:
    """Mirrors record_bill: posts Dr receivable_account, Cr income_account
    immediately -- the asset exists the moment the invoice is issued."""
    with transaction.atomic():
        entry = post_journal_entry(
            entity=entity,
            entry_date=invoice_date,
            description=(
                f"Invoice: {customer_name} - {description}" if description else f"Invoice: {customer_name}"
            ),
            created_by=created_by,
            lines=[
                JournalLineInput(account=receivable_account, currency=currency, debit_amount=amount),
                JournalLineInput(account=income_account, currency=currency, credit_amount=amount),
            ],
        )
        invoice = Invoice(
            entity=entity,
            customer_name=customer_name,
            description=description,
            invoice_date=invoice_date,
            due_date=due_date,
            amount=amount,
            currency=currency,
            income_account=income_account,
            receivable_account=receivable_account,
            journal_entry=entry,
            created_by=created_by,
        )
        invoice.full_clean()
        invoice.save()
    return invoice


@dataclass(frozen=True)
class InvoiceProgress:
    invoice: Invoice
    amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    status: str
    is_overdue: bool


def compute_invoice_progress(invoice: Invoice, *, as_of: date | None = None) -> InvoiceProgress:
    today = as_of or timezone.now().date()
    amount_paid = invoice.payments.aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]
    amount_due = invoice.amount - amount_paid

    if invoice.is_cancelled:
        status = "CANCELLED"
    elif amount_paid <= 0:
        status = "OPEN"
    elif amount_due > 0:
        status = "PARTIALLY_PAID"
    else:
        status = "PAID"

    is_overdue = status in ("OPEN", "PARTIALLY_PAID") and invoice.due_date < today

    return InvoiceProgress(
        invoice=invoice,
        amount=invoice.amount,
        amount_paid=amount_paid,
        amount_due=amount_due,
        status=status,
        is_overdue=is_overdue,
    )


def record_invoice_payment(*, invoice, payment_date, amount, payment_account, created_by) -> InvoicePayment:
    """payment_account is the account *receiving* the payment (still
    ASSET-typed), as opposed to record_bill_payment's payment_account
    being paid *from*."""
    if invoice.is_cancelled:
        raise AlreadyCancelledError("Cannot record a payment against a cancelled invoice.")
    progress = compute_invoice_progress(invoice)
    if amount > progress.amount_due:
        raise OverpaymentError(
            f"Payment of {amount} exceeds the remaining amount due of {progress.amount_due}."
        )

    with transaction.atomic():
        entry = post_journal_entry(
            entity=invoice.entity,
            entry_date=payment_date,
            description=f"Payment received: {invoice.customer_name}",
            created_by=created_by,
            lines=[
                JournalLineInput(
                    account=payment_account, currency=invoice.currency, debit_amount=amount
                ),
                JournalLineInput(
                    account=invoice.receivable_account, currency=invoice.currency, credit_amount=amount
                ),
            ],
        )
        payment = InvoicePayment(
            invoice=invoice,
            payment_date=payment_date,
            amount=amount,
            payment_account=payment_account,
            journal_entry=entry,
            created_by=created_by,
        )
        payment.full_clean()
        payment.save()
    return payment


def cancel_invoice(*, invoice, cancelled_by) -> Invoice:
    if invoice.is_cancelled:
        raise AlreadyCancelledError(f"Invoice '{invoice}' is already cancelled.")
    if invoice.payments.exists():
        raise HasPaymentsError(
            "Cannot cancel an invoice with recorded payments. Record an offsetting invoice instead."
        )
    with transaction.atomic():
        reverse_journal_entry(entry=invoice.journal_entry, reversed_by_user=cancelled_by)
        invoice.is_cancelled = True
        invoice.save(update_fields=["is_cancelled", "updated_at"])
    return invoice
