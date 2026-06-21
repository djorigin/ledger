from django.contrib import admin

from apps.ap_ar.models import Bill, BillPayment, Invoice, InvoicePayment


class BillPaymentInline(admin.TabularInline):
    model = BillPayment
    extra = 0
    fields = ["payment_date", "amount", "payment_account", "journal_entry"]
    autocomplete_fields = ["payment_account", "journal_entry"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ["vendor_name", "entity", "amount", "currency", "due_date", "is_cancelled"]
    list_filter = ["entity", "is_cancelled", "currency"]
    search_fields = ["vendor_name", "description"]
    autocomplete_fields = ["entity", "expense_account", "payable_account", "journal_entry", "created_by"]
    readonly_fields = ["journal_entry", "created_by", "created_at", "updated_at"]
    inlines = [BillPaymentInline]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0
    fields = ["payment_date", "amount", "payment_account", "journal_entry"]
    autocomplete_fields = ["payment_account", "journal_entry"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["customer_name", "entity", "amount", "currency", "due_date", "is_cancelled"]
    list_filter = ["entity", "is_cancelled", "currency"]
    search_fields = ["customer_name", "description"]
    autocomplete_fields = [
        "entity", "income_account", "receivable_account", "journal_entry", "created_by",
    ]
    readonly_fields = ["journal_entry", "created_by", "created_at", "updated_at"]
    inlines = [InvoicePaymentInline]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
