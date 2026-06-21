from django.contrib import admin

from apps.budgets.models import Budget, Project, SavingsGoal


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["account", "entity", "period_type", "period_start", "period_end", "budgeted_amount"]
    list_filter = ["period_type", "entity"]
    autocomplete_fields = ["entity", "account", "created_by"]


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ["name", "entity", "target_amount", "target_date", "linked_account"]
    list_filter = ["entity"]
    search_fields = ["name"]
    autocomplete_fields = ["entity", "linked_account", "created_by"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "entity", "status", "budget_amount", "currency", "target_completion_date"]
    list_filter = ["status", "entity", "currency"]
    search_fields = ["name"]
    autocomplete_fields = ["entity", "created_by"]
