from django.contrib import admin

from apps.imports.models import ColumnMapping, ImportBatch, ImportedTransaction


@admin.register(ColumnMapping)
class ColumnMappingAdmin(admin.ModelAdmin):
    list_display = ["name", "account", "amount_convention", "created_by", "created_at"]
    list_filter = ["amount_convention"]
    search_fields = ["name"]
    autocomplete_fields = ["account", "created_by"]


class ImportedTransactionInline(admin.TabularInline):
    model = ImportedTransaction
    extra = 0
    fields = ["transaction_date", "description", "amount", "status", "matched_line", "created_entry"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename", "account", "file_format", "status",
        "row_count", "duplicate_count", "imported_by", "created_at",
    ]
    list_filter = ["file_format", "status", "account"]
    search_fields = ["original_filename"]
    autocomplete_fields = ["account", "column_mapping", "imported_by"]
    inlines = [ImportedTransactionInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ImportedTransaction)
class ImportedTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_date", "description", "amount", "account", "status", "import_batch",
    ]
    list_filter = ["status", "account"]
    search_fields = ["description"]
    autocomplete_fields = ["account", "import_batch", "created_entry", "matched_by"]
    raw_id_fields = ["matched_line"]
