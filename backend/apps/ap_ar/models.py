import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.ap_ar.managers import BillQuerySet, InvoiceQuerySet
from apps.ledger.constants import validate_currency_code
from apps.ledger.models import AccountType


class Bill(models.Model):
    """
    Accounts Payable. Recording a bill posts a real JournalEntry
    immediately (Dr expense_account, Cr payable_account) -- the liability
    exists the moment the bill is received, whether or not it's been
    paid. Financial fields are immutable once created, same principle as
    JournalEntry itself; correcting a mistake means cancelling (which
    reverses journal_entry) and recording a new one.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey("entities.Entity", on_delete=models.PROTECT, related_name="bills")
    vendor_name = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    bill_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3, validators=[validate_currency_code])
    expense_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="bills_as_expense"
    )
    payable_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="bills_as_payable"
    )
    journal_entry = models.OneToOneField(
        "ledger.JournalEntry", on_delete=models.PROTECT, related_name="bill"
    )
    is_cancelled = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BillQuerySet.as_manager()

    class Meta:
        ordering = ["due_date", "vendor_name"]
        indexes = [models.Index(fields=["entity", "due_date"])]
        constraints = [
            models.CheckConstraint(
                check=Q(due_date__gte=models.F("bill_date")),
                name="bill_due_date_not_before_bill_date",
            ),
        ]

    def __str__(self):
        return f"Bill: {self.vendor_name} {self.amount} {self.currency} due {self.due_date}"

    def clean(self):
        super().clean()
        for field_name, expected_type in [
            ("expense_account", AccountType.EXPENSE),
            ("payable_account", AccountType.LIABILITY),
        ]:
            account = getattr(self, field_name, None)
            if account is None:
                continue
            if self.entity_id and account.entity_id != self.entity_id:
                raise ValidationError({field_name: _("Account must belong to the same entity.")})
            if account.account_type != expected_type:
                raise ValidationError(
                    {field_name: _("Account must be of type %(type)s.") % {"type": expected_type}}
                )
            if self.currency and account.native_currency != self.currency:
                raise ValidationError(
                    {field_name: _("Account currency must match the bill's currency.")}
                )


class BillPayment(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    payment_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="bill_payments"
    )
    journal_entry = models.OneToOneField(
        "ledger.JournalEntry", on_delete=models.PROTECT, related_name="bill_payment"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payment_date"]

    def __str__(self):
        return f"Payment {self.amount} on {self.bill}"

    def clean(self):
        super().clean()
        if self.payment_account_id and self.bill_id:
            if self.payment_account.entity_id != self.bill.entity_id:
                raise ValidationError(
                    {"payment_account": _("Account must belong to the same entity as the bill.")}
                )
            if self.payment_account.account_type != AccountType.ASSET:
                raise ValidationError(
                    {"payment_account": _("Payment account must be of type ASSET.")}
                )
            if self.payment_account.native_currency != self.bill.currency:
                raise ValidationError(
                    {"payment_account": _("Account currency must match the bill's currency.")}
                )


class Invoice(models.Model):
    """Accounts Receivable -- mirrors Bill exactly (see its docstring),
    with income_account/receivable_account instead of expense_account/
    payable_account."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey("entities.Entity", on_delete=models.PROTECT, related_name="invoices")
    customer_name = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3, validators=[validate_currency_code])
    income_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="invoices_as_income"
    )
    receivable_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="invoices_as_receivable"
    )
    journal_entry = models.OneToOneField(
        "ledger.JournalEntry", on_delete=models.PROTECT, related_name="invoice"
    )
    is_cancelled = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = InvoiceQuerySet.as_manager()

    class Meta:
        ordering = ["due_date", "customer_name"]
        indexes = [models.Index(fields=["entity", "due_date"])]
        constraints = [
            models.CheckConstraint(
                check=Q(due_date__gte=models.F("invoice_date")),
                name="invoice_due_date_not_before_invoice_date",
            ),
        ]

    def __str__(self):
        return f"Invoice: {self.customer_name} {self.amount} {self.currency} due {self.due_date}"

    def clean(self):
        super().clean()
        for field_name, expected_type in [
            ("income_account", AccountType.INCOME),
            ("receivable_account", AccountType.ASSET),
        ]:
            account = getattr(self, field_name, None)
            if account is None:
                continue
            if self.entity_id and account.entity_id != self.entity_id:
                raise ValidationError({field_name: _("Account must belong to the same entity.")})
            if account.account_type != expected_type:
                raise ValidationError(
                    {field_name: _("Account must be of type %(type)s.") % {"type": expected_type}}
                )
            if self.currency and account.native_currency != self.currency:
                raise ValidationError(
                    {field_name: _("Account currency must match the invoice's currency.")}
                )


class InvoicePayment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    payment_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="invoice_payments"
    )
    journal_entry = models.OneToOneField(
        "ledger.JournalEntry", on_delete=models.PROTECT, related_name="invoice_payment"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payment_date"]

    def __str__(self):
        return f"Payment {self.amount} on {self.invoice}"

    def clean(self):
        super().clean()
        if self.payment_account_id and self.invoice_id:
            if self.payment_account.entity_id != self.invoice.entity_id:
                raise ValidationError(
                    {"payment_account": _("Account must belong to the same entity as the invoice.")}
                )
            if self.payment_account.account_type != AccountType.ASSET:
                raise ValidationError(
                    {"payment_account": _("Payment account must be of type ASSET.")}
                )
            if self.payment_account.native_currency != self.invoice.currency:
                raise ValidationError(
                    {"payment_account": _("Account currency must match the invoice's currency.")}
                )
