from decimal import Decimal

from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.entities.models import Entity
from apps.ledger.exceptions import LedgerError
from apps.ledger.models import Account, JournalEntry, JournalLine
from apps.ledger.services import JournalLineInput, post_journal_entry


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id", "entity", "parent", "account_type", "name", "code",
            "native_currency", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = fields


class JournalLineReadSerializer(serializers.ModelSerializer):
    debit_amount = MoneyField()
    credit_amount = MoneyField()

    class Meta:
        model = JournalLine
        fields = ["id", "account", "debit_amount", "credit_amount", "currency", "description"]
        read_only_fields = fields


class JournalLineWriteSerializer(serializers.Serializer):
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    currency = serializers.CharField(max_length=3)
    debit_amount = MoneyField(default=Decimal("0"))
    credit_amount = MoneyField(default=Decimal("0"))
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class JournalEntrySerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    lines = JournalLineWriteSerializer(many=True, write_only=True)
    lines_detail = JournalLineReadSerializer(source="lines", many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    reverses = serializers.PrimaryKeyRelatedField(read_only=True)
    reversed_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id", "entity", "entry_date", "description", "memo", "status",
            "created_by", "created_at", "posted_at",
            "reverses", "reversed_by",
            "lines", "lines_detail",
        ]
        read_only_fields = [
            "id", "status", "created_by", "created_at", "posted_at",
            "reverses", "reversed_by",
        ]

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        line_inputs = [
            JournalLineInput(
                account=line["account"],
                currency=line["currency"],
                debit_amount=line.get("debit_amount", Decimal("0")),
                credit_amount=line.get("credit_amount", Decimal("0")),
                description=line.get("description", ""),
            )
            for line in lines_data
        ]
        request = self.context["request"]
        try:
            return post_journal_entry(
                entity=validated_data["entity"],
                entry_date=validated_data["entry_date"],
                description=validated_data["description"],
                memo=validated_data.get("memo", ""),
                lines=line_inputs,
                created_by=request.user,
            )
        except LedgerError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc


class JournalEntryReverseSerializer(serializers.Serializer):
    reversal_date = serializers.DateField(required=False)
