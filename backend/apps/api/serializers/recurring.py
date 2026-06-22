from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.entities.models import Entity
from apps.ledger.models import Account
from apps.recurring.models import PendingRecurringEntry, RecurringTransactionTemplate


class RecurringTransactionTemplateSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    debit_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    credit_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    amount = MoneyField()
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = RecurringTransactionTemplate
        fields = [
            "id", "entity", "description", "debit_account", "credit_account",
            "amount", "currency", "frequency", "start_date", "end_date",
            "next_due_date", "is_active",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class PendingRecurringEntrySerializer(serializers.ModelSerializer):
    amount = MoneyField()
    template_description = serializers.CharField(source="template.description", read_only=True)
    template_currency = serializers.CharField(source="template.currency", read_only=True)

    class Meta:
        model = PendingRecurringEntry
        fields = [
            "id", "template", "template_description", "template_currency", "due_date", "amount",
            "status", "journal_entry", "reviewed_by", "reviewed_at", "created_at",
        ]
        read_only_fields = fields


class ApprovePendingEntrySerializer(serializers.Serializer):
    amount = MoneyField(required=False)
