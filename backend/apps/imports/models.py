import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.imports.managers import (
    ColumnMappingQuerySet,
    ImportBatchQuerySet,
    ImportedTransactionQuerySet,
)


class AmountConvention(models.TextChoices):
    SIGNED_AMOUNT = "SIGNED_AMOUNT", _("Single signed amount column")
    DEBIT_CREDIT = "DEBIT_CREDIT", _("Separate debit/credit columns")


class ColumnMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        "ledger.Account", on_delete=models.CASCADE, related_name="column_mappings"
    )
    name = models.CharField(max_length=255)

    date_column = models.CharField(max_length=255)
    date_format = models.CharField(max_length=64)
    description_column = models.CharField(max_length=255)
    memo_column = models.CharField(max_length=255, blank=True)

    amount_convention = models.CharField(max_length=16, choices=AmountConvention.choices)
    amount_column = models.CharField(max_length=255, blank=True)
    debit_column = models.CharField(max_length=255, blank=True)
    credit_column = models.CharField(max_length=255, blank=True)
    # Some banks encode debit/credit as one unsigned amount column plus a
    # separate type indicator (e.g. a "Type" column containing "Debit"/
    # "Credit") rather than two amount columns. Kept optional/blank for the
    # common two-column case.
    type_column = models.CharField(max_length=255, blank=True)
    type_debit_value = models.CharField(max_length=64, blank=True)

    balance_column = models.CharField(max_length=255, blank=True)
    has_header_row = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ColumnMappingQuerySet.as_manager()

    class Meta:
        ordering = ["account", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "name"], name="unique_mapping_name_per_account"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.account})"

    def clean(self):
        super().clean()
        if self.amount_convention == AmountConvention.SIGNED_AMOUNT and not self.amount_column:
            raise ValidationError(
                {"amount_column": _("Required for the signed-amount convention.")}
            )
        if self.amount_convention == AmountConvention.DEBIT_CREDIT and not (
            self.debit_column or self.credit_column
        ):
            raise ValidationError(
                {"debit_column": _("At least one of debit_column/credit_column is required.")}
            )


class ImportFileFormat(models.TextChoices):
    CSV = "CSV", _("CSV")
    OFX = "OFX", _("OFX")


class ImportBatchStatus(models.TextChoices):
    PREVIEW = "PREVIEW", _("Preview")
    IMPORTED = "IMPORTED", _("Imported")
    FAILED = "FAILED", _("Failed")


class ImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="import_batches"
    )
    file_format = models.CharField(max_length=8, choices=ImportFileFormat.choices)
    original_filename = models.CharField(max_length=255)
    column_mapping = models.ForeignKey(
        ColumnMapping,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_batches",
    )
    status = models.CharField(
        max_length=16, choices=ImportBatchStatus.choices, default=ImportBatchStatus.PREVIEW
    )
    statement_start_date = models.DateField(null=True, blank=True)
    statement_end_date = models.DateField(null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    objects = ImportBatchQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["account", "-created_at"])]

    def __str__(self):
        return f"{self.original_filename} -> {self.account} ({self.status})"


class ImportedTransactionStatus(models.TextChoices):
    UNMATCHED = "UNMATCHED", _("Unmatched")
    MATCHED = "MATCHED", _("Matched")
    POSTED = "POSTED", _("Posted")
    IGNORED = "IGNORED", _("Ignored")


class ImportedTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="transactions"
    )
    # Denormalized off import_batch.account: every matching/dedup query
    # filters by account, and the dedup UniqueConstraint can't span a join.
    account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="imported_transactions"
    )

    transaction_date = models.DateField()
    description = models.CharField(max_length=500)
    memo = models.CharField(max_length=500, blank=True)
    # Signed from the bank statement's own point of view: positive = money
    # in, negative = money out. Deliberately not named debit_amount/
    # credit_amount -- that's the ledger's convention, which is the inverse
    # for an asset account. Parsers normalize every source format to this.
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    running_balance = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)

    # OFX FITID verbatim, or a synthesized hash for CSV -- see services.py.
    external_id = models.CharField(max_length=255)

    status = models.CharField(
        max_length=16,
        choices=ImportedTransactionStatus.choices,
        default=ImportedTransactionStatus.UNMATCHED,
    )
    matched_line = models.ForeignKey(
        "ledger.JournalLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_imports",
    )
    created_entry = models.ForeignKey(
        "ledger.JournalEntry", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    matched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    matched_at = models.DateTimeField(null=True, blank=True)

    raw_row = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImportedTransactionQuerySet.as_manager()

    class Meta:
        ordering = ["-transaction_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "external_id"],
                name="unique_imported_transaction_per_account_external_id",
            ),
            models.CheckConstraint(
                check=Q(matched_line__isnull=True) | Q(created_entry__isnull=True),
                name="imported_transaction_not_both_matched_and_created",
            ),
        ]
        indexes = [
            models.Index(fields=["account", "status"]),
            models.Index(fields=["account", "transaction_date"]),
        ]

    def __str__(self):
        return f"{self.transaction_date} {self.description} {self.amount} ({self.status})"
