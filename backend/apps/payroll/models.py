import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.ledger.constants import validate_currency_code
from apps.payroll.managers import PayslipQuerySet


class Payslip(models.Model):
    """
    A dedicated payslip entry for one employer (KCC). Each fortnightly
    payslip auto-generates a balanced JournalEntry via
    apps.payroll.services.record_payslip/update_payslip -- never a direct
    ORM save bypassing the ledger's one sanctioned write path
    (post_journal_entry). Wife's income is separate, plain net-amount
    journal entries via the existing transaction entry flow -- no payslip
    model needed there.

    Financial fields are conceptually immutable once posted, same
    principle as Bill/Invoice/JournalEntry itself: editing after
    `journal_entry` is set reverses the original entry and posts a fresh
    one (see update_payslip), rather than mutating a posted entry in place.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey("entities.Entity", on_delete=models.PROTECT, related_name="payslips")
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    payment_date = models.DateField()
    currency = models.CharField(max_length=3, validators=[validate_currency_code])

    gross_amount = models.DecimalField(max_digits=19, decimal_places=4)

    # Post-tax deductions (reduce net pay, not taxable gross)
    deduction_tax = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    deduction_fuel_card = models.DecimalField(
        max_digits=19, decimal_places=4, default=0,
        help_text="Personal expense recovery -- fuel card benefit repayment",
    )
    deduction_social_club = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    deduction_cfmeu = models.DecimalField(
        max_digits=19, decimal_places=4, default=0, help_text="CFMEU union dues"
    )

    # Pre-tax deduction (reduces taxable gross -- vehicle/equipment lease)
    deduction_pretax_lease = models.DecimalField(
        max_digits=19, decimal_places=4, default=0,
        help_text="Pre-tax salary sacrifice -- vehicle or equipment lease",
    )

    # Computed -- stored for audit trail, always recomputed/verified on
    # save, never trusted from the caller.
    net_pay = models.DecimalField(max_digits=19, decimal_places=4)

    # The six accounts the auto-generated journal entry posts to. Explicit
    # FKs, not a settings-file name lookup -- matches every other model in
    # this codebase (Budget.account, Bill.expense_account, etc.).
    income_account = models.ForeignKey("ledger.Account", on_delete=models.PROTECT, related_name="+")
    pretax_lease_expense_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="+"
    )
    tax_expense_account = models.ForeignKey("ledger.Account", on_delete=models.PROTECT, related_name="+")
    fuel_card_expense_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="+"
    )
    social_club_expense_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="+"
    )
    cfmeu_expense_account = models.ForeignKey("ledger.Account", on_delete=models.PROTECT, related_name="+")
    bank_account = models.ForeignKey("ledger.Account", on_delete=models.PROTECT, related_name="+")

    journal_entry = models.OneToOneField(
        "ledger.JournalEntry", on_delete=models.PROTECT, null=True, blank=True, related_name="payslip"
    )

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PayslipQuerySet.as_manager()

    class Meta:
        ordering = ["-payment_date"]
        indexes = [models.Index(fields=["entity", "payment_date"])]

    def __str__(self):
        return f"Payslip {self.pay_period_start}..{self.pay_period_end} ({self.net_pay} {self.currency})"

    def expected_net_pay(self):
        return (
            self.gross_amount
            - self.deduction_pretax_lease
            - self.deduction_tax
            - self.deduction_fuel_card
            - self.deduction_social_club
            - self.deduction_cfmeu
        )

    def clean(self):
        super().clean()
        if self.net_pay != self.expected_net_pay():
            raise ValidationError(
                {
                    "net_pay": _(
                        "net_pay (%(given)s) does not match the computed value (%(expected)s)."
                    )
                    % {"given": self.net_pay, "expected": self.expected_net_pay()}
                }
            )
        account_fields = [
            "income_account",
            "pretax_lease_expense_account",
            "tax_expense_account",
            "fuel_card_expense_account",
            "social_club_expense_account",
            "cfmeu_expense_account",
            "bank_account",
        ]
        for field_name in account_fields:
            account = getattr(self, field_name, None)
            if account is None:
                continue
            if self.entity_id and account.entity_id != self.entity_id:
                raise ValidationError({field_name: _("Account must belong to the same entity.")})
            if self.currency and account.native_currency != self.currency:
                raise ValidationError(
                    {field_name: _("Account currency must match the payslip's currency.")}
                )
