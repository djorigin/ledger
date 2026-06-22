from django.contrib import admin

from apps.recurring.models import PendingRecurringEntry, RecurringTransactionTemplate


@admin.register(RecurringTransactionTemplate)
class RecurringTransactionTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "description", "entity", "frequency", "amount", "currency", "next_due_date", "is_active",
    ]
    list_filter = ["entity", "frequency", "is_active"]
    search_fields = ["description"]
    autocomplete_fields = ["entity", "debit_account", "credit_account", "created_by"]


@admin.register(PendingRecurringEntry)
class PendingRecurringEntryAdmin(admin.ModelAdmin):
    list_display = ["template", "due_date", "amount", "status", "reviewed_by", "reviewed_at"]
    list_filter = ["status"]
    autocomplete_fields = ["template", "journal_entry", "reviewed_by"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
