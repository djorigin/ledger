from django.contrib import admin

from apps.inventory.models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        "name", "entity", "category", "estimated_replacement_value", "currency", "insured", "is_active",
    ]
    list_filter = ["entity", "category", "insured", "is_active"]
    search_fields = ["name", "brand", "model_number", "serial_number"]
    autocomplete_fields = ["entity", "created_by"]
