from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.budgets.models import Budget, Project, SavingsGoal
from apps.entities.models import Entity
from apps.ledger.models import Account


class BudgetSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    budgeted_amount = MoneyField()
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Budget
        fields = [
            "id", "entity", "account", "name", "period_type", "period_start",
            "period_end", "budgeted_amount", "include_descendants", "notes",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class BudgetProgressSerializer(serializers.Serializer):
    budgeted_amount = MoneyField()
    actual_amount = MoneyField()
    remaining_amount = MoneyField()
    percent_used = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)


class SavingsGoalSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    linked_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    target_amount = MoneyField()
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = SavingsGoal
        fields = [
            "id", "entity", "name", "target_amount", "target_date",
            "linked_account", "notes", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class SavingsGoalProgressSerializer(serializers.Serializer):
    current_balance = MoneyField()
    target_amount = MoneyField()
    remaining_amount = MoneyField()
    percent_complete = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
    days_remaining = serializers.IntegerField()


class ProjectSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    budget_amount = MoneyField()
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "entity", "name", "description", "budget_amount", "currency",
            "status", "start_date", "target_completion_date",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class ProjectProgressSerializer(serializers.Serializer):
    actual_to_date = MoneyField()
    budget_amount = MoneyField()
    remaining_amount = MoneyField()
    percent_used = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)


class SuperannuationProjectionRequestSerializer(serializers.Serializer):
    current_balance = MoneyField()
    target_date = serializers.DateField()
    annual_contribution = MoneyField()
    annual_growth_rate = serializers.DecimalField(max_digits=6, decimal_places=4)


class SuperannuationProjectionResponseSerializer(serializers.Serializer):
    projected_balance = MoneyField()
