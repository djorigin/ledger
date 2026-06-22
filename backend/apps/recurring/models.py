import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.ledger.constants import validate_currency_code
from apps.recurring.managers import PendingRecurringEntryQuerySet, RecurringTransactionTemplateQuerySet


class RecurrenceFrequency(models.TextChoices):
    WEEKLY = "WEEKLY", _("Weekly")
    MONTHLY = "MONTHLY", _("Monthly")
    QUARTERLY = "QUARTERLY", _("Quarterly")
    ANNUALLY = "ANNUALLY", _("Annually")


class RecurringTransactionTemplate(models.Model):
    """
    Defines a recurring entry (mortgage payment, salary, subscription).
    Generation (apps.recurring.services.generate_due_recurring_entries)
    never posts a JournalEntry directly -- it only creates a reviewable
    PendingRecurringEntry. Unlike Bill/Invoice, a template is an editable
    setting, not a financial transaction itself, so it has no immutability
    constraint -- editing it doesn't touch any already-posted entry.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(
        "entities.Entity", on_delete=models.PROTECT, related_name="recurring_templates"
    )
    description = models.CharField(max_length=500)
    debit_account = models.ForeignKey("ledger.Account", on_delete=models.PROTECT, related_name="+")
    credit_account = models.ForeignKey("ledger.Account", on_delete=models.PROTECT, related_name="+")
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3, validators=[validate_currency_code])
    frequency = models.CharField(max_length=16, choices=RecurrenceFrequency.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RecurringTransactionTemplateQuerySet.as_manager()

    class Meta:
        ordering = ["next_due_date", "description"]
        indexes = [models.Index(fields=["entity", "is_active", "next_due_date"])]

    def __str__(self):
        return f"{self.description} ({self.frequency}, next {self.next_due_date})"

    def clean(self):
        super().clean()
        if self.debit_account_id and self.credit_account_id and self.debit_account_id == self.credit_account_id:
            raise ValidationError(
                {"credit_account": _("Debit and credit accounts must be different.")}
            )
        for field_name in ("debit_account", "credit_account"):
            account = getattr(self, field_name, None)
            if account is None:
                continue
            if self.entity_id and account.entity_id != self.entity_id:
                raise ValidationError({field_name: _("Account must belong to the same entity.")})
            if self.currency and account.native_currency != self.currency:
                raise ValidationError(
                    {field_name: _("Account currency must match the template's currency.")}
                )


class PendingEntryStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    DISMISSED = "DISMISSED", _("Dismissed")


class PendingRecurringEntry(models.Model):
    """
    One reviewable occurrence generated from a template. Approving posts a
    real JournalEntry via record_simple_transaction; dismissing never
    posts anything. amount is copied from the template at generation time
    but editable at approval (e.g. a variable electricity bill).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        RecurringTransactionTemplate, on_delete=models.PROTECT, related_name="pending_entries"
    )
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=19, decimal_places=4)
    status = models.CharField(
        max_length=16, choices=PendingEntryStatus.choices, default=PendingEntryStatus.PENDING
    )
    journal_entry = models.ForeignKey(
        "ledger.JournalEntry", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PendingRecurringEntryQuerySet.as_manager()

    class Meta:
        ordering = ["due_date"]
        constraints = [
            models.UniqueConstraint(fields=["template", "due_date"], name="unique_template_due_date"),
        ]

    def __str__(self):
        return f"{self.template.description} due {self.due_date} ({self.status})"

    @property
    def entity(self):
        """
        Satisfies apps.api.permissions._resolve_entity's `hasattr(obj,
        "entity")` check -- this object has neither a direct `.entity` nor
        an `.account` (the function's two existing fallback shapes), only
        `.template.entity`.
        """
        return self.template.entity
