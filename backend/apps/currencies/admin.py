from django.contrib import admin

from apps.currencies.models import ExchangeRate


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["date", "from_currency", "to_currency", "rate", "source"]
    list_filter = ["from_currency", "to_currency", "source"]
    search_fields = ["from_currency", "to_currency"]
    ordering = ["-date"]

    def has_change_permission(self, request, obj=None):
        return False
