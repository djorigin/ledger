from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.imports.models import ColumnMapping, ImportBatch, ImportedTransaction, ImportFileFormat
from apps.ledger.models import Account, JournalLine, ReconciliationRecord


class ColumnMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColumnMapping
        fields = [
            "id", "account", "name", "date_column", "date_format",
            "description_column", "memo_column", "amount_convention",
            "amount_column", "debit_column", "credit_column",
            "type_column", "type_debit_value", "balance_column",
            "has_header_row", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class InlineMappingFieldsSerializer(serializers.Serializer):
    """
    Shared by preview and confirm: lets the caller describe a CSV mapping
    inline (not yet saved as a ColumnMapping) so preview can show a
    properly-mapped sample before anything is persisted. All optional since
    OFX needs none of this and a CSV call may instead pass an existing
    `column_mapping` id.
    """

    date_column = serializers.CharField(required=False, allow_blank=True)
    date_format = serializers.CharField(required=False, allow_blank=True)
    description_column = serializers.CharField(required=False, allow_blank=True)
    memo_column = serializers.CharField(required=False, allow_blank=True)
    amount_convention = serializers.ChoiceField(
        choices=["SIGNED_AMOUNT", "DEBIT_CREDIT"], required=False, allow_blank=True
    )
    amount_column = serializers.CharField(required=False, allow_blank=True)
    debit_column = serializers.CharField(required=False, allow_blank=True)
    credit_column = serializers.CharField(required=False, allow_blank=True)
    type_column = serializers.CharField(required=False, allow_blank=True)
    type_debit_value = serializers.CharField(required=False, allow_blank=True)
    balance_column = serializers.CharField(required=False, allow_blank=True)
    # No default here -- parse_csv()/ColumnMapping already default this to
    # True. A serializer-level default would make this field always present
    # in validated_data, defeating the "were any mapping fields supplied at
    # all" check in _extract_inline_mapping_data().
    has_header_row = serializers.BooleanField(required=False)


class ImportPreviewRequestSerializer(InlineMappingFieldsSerializer):
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    file_format = serializers.ChoiceField(choices=ImportFileFormat.choices)
    file = serializers.FileField()
    column_mapping = serializers.PrimaryKeyRelatedField(
        queryset=ColumnMapping.objects.all(), required=False, allow_null=True
    )


class ImportPreviewResponseSerializer(serializers.Serializer):
    file_format = serializers.CharField()
    mapped = serializers.BooleanField()
    headers = serializers.ListField(child=serializers.CharField(), required=False)
    preview_rows = serializers.ListField(child=serializers.DictField())
    total_row_count = serializers.IntegerField()
    available_mappings = ColumnMappingSerializer(many=True, required=False)


class ImportConfirmRequestSerializer(InlineMappingFieldsSerializer):
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    file_format = serializers.ChoiceField(choices=ImportFileFormat.choices)
    file = serializers.FileField()
    column_mapping = serializers.PrimaryKeyRelatedField(
        queryset=ColumnMapping.objects.all(), required=False, allow_null=True
    )
    save_mapping_as = serializers.CharField(required=False, allow_blank=True)


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = [
            "id", "account", "file_format", "original_filename", "column_mapping",
            "status", "statement_start_date", "statement_end_date",
            "row_count", "duplicate_count", "imported_by", "created_at", "confirmed_at",
        ]
        read_only_fields = fields


class ImportedTransactionSerializer(serializers.ModelSerializer):
    amount = MoneyField()
    running_balance = MoneyField(required=False, allow_null=True)

    class Meta:
        model = ImportedTransaction
        fields = [
            "id", "import_batch", "account", "transaction_date", "description",
            "memo", "amount", "running_balance", "external_id", "status",
            "matched_line", "created_entry", "matched_by", "matched_at",
        ]
        read_only_fields = fields


class ConfirmMatchSerializer(serializers.Serializer):
    journal_line = serializers.PrimaryKeyRelatedField(queryset=JournalLine.objects.all())


class CreateEntryFromImportSerializer(serializers.Serializer):
    offsetting_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ReconciliationRecordSerializer(serializers.ModelSerializer):
    statement_balance = MoneyField()

    class Meta:
        model = ReconciliationRecord
        fields = [
            "id", "account", "statement_date", "statement_balance",
            "reconciled_by", "reconciled_at", "notes",
        ]
        # account is resolved from the URL, not the request body.
        read_only_fields = ["id", "account", "reconciled_by", "reconciled_at"]
