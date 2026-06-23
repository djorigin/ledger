from django.contrib import admin

from apps.payroll.models import Payslip


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    """Inspection only -- data entry happens via the API (and, later, a
    frontend), never directly through Admin. Mirrors the read-only
    registration pattern used for ReconciliationRecord."""

    list_display = ["entity", "pay_period_start", "pay_period_end", "gross_amount", "net_pay", "currency"]
    list_filter = ["entity", "currency"]
    search_fields = ["notes"]
    autocomplete_fields = [
        "entity", "income_account", "pretax_lease_expense_account", "tax_expense_account",
        "fuel_card_expense_account", "social_club_expense_account", "cfmeu_expense_account",
        "bank_account", "journal_entry", "created_by",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
