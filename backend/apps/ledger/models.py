import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.ledger.exceptions import JournalEntryImmutableError
from apps.ledger.managers import AccountQuerySet, JournalEntryQuerySet


class AccountType(models.TextChoices):
    ASSET = "ASSET", _("Asset")
    LIABILITY = "LIABILITY", _("Liability")
    EQUITY = "EQUITY", _("Equity")
    INCOME = "INCOME", _("Income")
    EXPENSE = "EXPENSE", _("Expense")


class DebitCredit(models.TextChoices):
    DEBIT = "DEBIT", _("Debit")
    CREDIT = "CREDIT", _("Credit")


NORMAL_BALANCE = {
    AccountType.ASSET: DebitCredit.DEBIT,
    AccountType.EXPENSE: DebitCredit.DEBIT,
    AccountType.LIABILITY: DebitCredit.CREDIT,
    AccountType.EQUITY: DebitCredit.CREDIT,
    AccountType.INCOME: DebitCredit.CREDIT,
}


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(
        "entities.Entity", on_delete=models.PROTECT, related_name="accounts"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    account_type = models.CharField(max_length=16, choices=AccountType.choices)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, blank=True)
    native_currency = models.CharField(max_length=3)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountQuerySet.as_manager()

    class Meta:
        ordering = ["entity", "account_type", "name"]
        indexes = [models.Index(fields=["entity", "account_type"])]

    def __str__(self):
        return f"{self.name} ({self.entity})"

    @property
    def normal_balance(self):
        return NORMAL_BALANCE[self.account_type]

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.parent.entity_id != self.entity_id:
                raise ValidationError(
                    {"parent": _("Parent account must belong to the same entity.")}
                )
            if self.parent.account_type != self.account_type:
                raise ValidationError(
                    {"account_type": _("Account type must match its parent's account type.")}
                )


class JournalEntryStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    POSTED = "POSTED", _("Posted")
    REVERSED = "REVERSED", _("Reversed")


class JournalEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(
        "entities.Entity", on_delete=models.PROTECT, related_name="journal_entries"
    )
    entry_date = models.DateField()
    description = models.CharField(max_length=500)
    memo = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=JournalEntryStatus.choices, default=JournalEntryStatus.POSTED
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    reverses = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversed_by",
    )

    objects = JournalEntryQuerySet.as_manager()

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        indexes = [models.Index(fields=["entity", "entry_date"])]

    def __str__(self):
        return f"{self.entry_date} {self.description} ({self.entity})"

    def delete(self, *args, **kwargs):
        raise JournalEntryImmutableError(
            "JournalEntry rows are never hard-deleted. Use reverse_journal_entry() "
            "to record a correcting entry instead."
        )

    def mark_reversed(self, by_user):
        self.status = JournalEntryStatus.REVERSED
        self.updated_by = by_user
        self.save(update_fields=["status", "updated_by", "updated_at"])


class JournalLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.PROTECT, related_name="lines"
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    debit_amount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0"))
    credit_amount = models.DecimalField(max_digits=19, decimal_places=4, default=Decimal("0"))
    currency = models.CharField(max_length=3)
    description = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(debit_amount__gt=0, credit_amount=0)
                    | Q(credit_amount__gt=0, debit_amount=0)
                ),
                name="journal_line_exactly_one_side_nonzero",
            ),
        ]

    def __str__(self):
        side = "Dr" if self.debit_amount else "Cr"
        amount = self.debit_amount or self.credit_amount
        return f"{side} {self.account} {amount} {self.currency}"

    def clean(self):
        super().clean()
        debit_positive = self.debit_amount and self.debit_amount > 0
        credit_positive = self.credit_amount and self.credit_amount > 0
        if debit_positive == credit_positive:
            raise ValidationError(
                _("Exactly one of debit_amount or credit_amount must be greater than zero.")
            )
