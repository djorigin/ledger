import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.budgets.managers import BudgetQuerySet, ProjectQuerySet, SavingsGoalQuerySet
from apps.ledger.constants import validate_currency_code


class BudgetPeriodType(models.TextChoices):
    MONTHLY = "MONTHLY", _("Monthly")
    ANNUAL = "ANNUAL", _("Annual")
    CUSTOM = "CUSTOM", _("Custom")


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey("entities.Entity", on_delete=models.PROTECT, related_name="budgets")
    account = models.ForeignKey("ledger.Account", on_delete=models.PROTECT, related_name="budgets")
    name = models.CharField(max_length=255, blank=True)
    period_type = models.CharField(max_length=16, choices=BudgetPeriodType.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    budgeted_amount = models.DecimalField(max_digits=19, decimal_places=4)
    # Explicit opt-out for rolling up child accounts (e.g. budgeting the
    # parent "Groceries" account also counts its sub-accounts) -- no
    # currency field here, always the account's own native_currency.
    include_descendants = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BudgetQuerySet.as_manager()

    class Meta:
        ordering = ["-period_start", "account__name"]
        indexes = [models.Index(fields=["entity", "account", "period_start"])]
        constraints = [
            models.CheckConstraint(
                check=Q(period_end__gte=models.F("period_start")),
                name="budget_period_end_not_before_start",
            ),
        ]

    def __str__(self):
        return f"{self.account} budget {self.period_start}..{self.period_end}"

    def clean(self):
        super().clean()
        if self.account_id and self.entity_id and self.account.entity_id != self.entity_id:
            raise ValidationError({"account": _("Budget account must belong to the same entity.")})


class SavingsGoal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(
        "entities.Entity", on_delete=models.PROTECT, related_name="savings_goals"
    )
    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=19, decimal_places=4)
    target_date = models.DateField()
    # No separate currency field -- always linked_account.native_currency,
    # and no cross-currency support (the goal and account are assumed to
    # share a currency; see step 7 design notes).
    linked_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="savings_goals"
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SavingsGoalQuerySet.as_manager()

    class Meta:
        ordering = ["target_date", "name"]
        indexes = [models.Index(fields=["entity", "target_date"])]

    def __str__(self):
        return f"{self.name} (target {self.target_amount} by {self.target_date})"

    def clean(self):
        super().clean()
        if (
            self.linked_account_id
            and self.entity_id
            and self.linked_account.entity_id != self.entity_id
        ):
            raise ValidationError(
                {"linked_account": _("Linked account must belong to the same entity.")}
            )


class ProjectStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey("entities.Entity", on_delete=models.PROTECT, related_name="projects")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    budget_amount = models.DecimalField(max_digits=19, decimal_places=4)
    # Its own currency field, unlike Budget/SavingsGoal -- a project's
    # tagged entries can span multiple accounts of different currencies,
    # so there's no single account to derive it from.
    currency = models.CharField(max_length=3, validators=[validate_currency_code])
    status = models.CharField(
        max_length=16, choices=ProjectStatus.choices, default=ProjectStatus.ACTIVE
    )
    start_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity", "status"])]

    def __str__(self):
        return f"{self.name} ({self.entity})"
