from django.contrib import admin

from apps.assets.models import AssetClass, AssetValuation


class AssetValuationInline(admin.TabularInline):
    model = AssetValuation
    extra = 0
    fields = ["valuation_date", "current_value", "currency", "source", "notes", "created_by"]
    autocomplete_fields = ["created_by"]


@admin.register(AssetClass)
class AssetClassAdmin(admin.ModelAdmin):
    list_display = ["name", "entity", "category", "currency", "is_active"]
    list_filter = ["entity", "category", "is_active"]
    search_fields = ["name"]
    autocomplete_fields = ["entity", "created_by"]
    inlines = [AssetValuationInline]


@admin.register(AssetValuation)
class AssetValuationAdmin(admin.ModelAdmin):
    list_display = ["asset", "valuation_date", "current_value", "currency", "source"]
    list_filter = ["valuation_date"]
    autocomplete_fields = ["asset", "created_by"]
