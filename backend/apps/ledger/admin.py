from django.contrib import admin

from apps.ledger.models import Account, JournalEntry, JournalLine, ReconciliationRecord


class AccountInline(admin.TabularInline):
    model = Account
    fk_name = "parent"
    extra = 0
    fields = ["name", "account_type", "code", "native_currency", "is_active", "is_cash_equivalent"]
    show_change_link = True


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        "name", "account_type", "entity", "parent", "native_currency",
        "is_active", "is_cash_equivalent",
    ]
    # entity then account_type -- groups e.g. all of a household's
    # LIABILITY accounts (credit cards, loans, mortgages) together,
    # matching the model's own Meta.ordering.
    ordering = ["entity", "account_type", "name"]
    list_filter = ["account_type", "entity", "native_currency", "is_active", "is_cash_equivalent"]
    search_fields = ["name", "code"]
    autocomplete_fields = ["entity", "parent"]
    inlines = [AccountInline]


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0
    fields = ["account", "debit_amount", "credit_amount", "currency", "description", "cleared"]
    autocomplete_fields = ["account"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["entry_date", "entity", "description", "status", "created_by", "created_at"]
    list_filter = ["status", "entity"]
    search_fields = ["description", "memo"]
    autocomplete_fields = ["entity", "created_by", "updated_by", "reverses"]
    readonly_fields = [
        "status",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "posted_at",
        "reverses",
    ]
    inlines = [JournalLineInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReconciliationRecord)
class ReconciliationRecordAdmin(admin.ModelAdmin):
    list_display = ["account", "statement_date", "statement_balance", "reconciled_by", "reconciled_at"]
    list_filter = ["account"]
    autocomplete_fields = ["account", "reconciled_by"]

    def has_change_permission(self, request, obj=None):
        return False
