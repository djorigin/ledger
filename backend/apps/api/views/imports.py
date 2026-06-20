from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasEntityRole
from apps.api.serializers.imports import (
    ColumnMappingSerializer,
    ConfirmMatchSerializer,
    CreateEntryFromImportSerializer,
    ImportBatchSerializer,
    ImportConfirmRequestSerializer,
    ImportedTransactionSerializer,
    ImportPreviewRequestSerializer,
    ImportPreviewResponseSerializer,
    ReconciliationRecordSerializer,
)
from apps.api.serializers.ledger import JournalLineReadSerializer
from apps.entities.models import EntityRole
from apps.imports.exceptions import ImportError_
from apps.imports.models import ColumnMapping, ImportBatch, ImportedTransaction
from apps.imports.services import (
    confirm_import,
    confirm_match,
    create_entry_from_import,
    find_candidate_matches,
    ignore_imported_transaction,
    parse_preview,
)
from apps.ledger.exceptions import LedgerError
from apps.ledger.models import Account
from apps.ledger.services import mark_account_reconciled


class ColumnMappingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ColumnMappingSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = ColumnMapping.objects.accessible_by(self.request.user).select_related("account")
        account_id = self.request.query_params.get("account")
        if account_id:
            qs = qs.filter(account_id=account_id)
        return qs

    def get_permissions(self):
        if self.action == "create":
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ImportBatchViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Plain list/retrieve -- preview/confirm are separate endpoints below
    since the request shape (file + format + mapping) doesn't map onto a
    single ModelSerializer.create() cleanly."""

    serializer_class = ImportBatchSerializer
    http_method_names = ["get", "head", "options"]
    permission_classes = [HasEntityRole(EntityRole.VIEWER)]

    def get_queryset(self):
        qs = ImportBatch.objects.accessible_by(self.request.user).select_related(
            "account", "column_mapping", "imported_by"
        )
        account_id = self.request.query_params.get("account")
        if account_id:
            qs = qs.filter(account_id=account_id)
        return qs

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        batch = self.get_object()
        transactions = batch.transactions.select_related("matched_line", "created_entry")
        return Response(ImportedTransactionSerializer(transactions, many=True).data)


_INLINE_MAPPING_FIELDS = [
    "date_column", "date_format", "description_column", "memo_column",
    "amount_convention", "amount_column", "debit_column", "credit_column",
    "type_column", "type_debit_value", "balance_column", "has_header_row",
]


def _extract_inline_mapping_data(raw_data, validated_data):
    """
    Pulls whichever inline mapping fields were actually supplied (CSV, no
    saved mapping picked) out of validated request data. An inline mapping
    is only considered "provided" if date_column is set -- that's required
    for any valid mapping, and unlike has_header_row it's a plain CharField
    not subject to DRF's checkbox-style auto-defaulting.

    has_header_row needs special handling: DRF's BooleanField silently
    defaults a *missing* field to False for multipart/form-encoded
    requests (mimicking how an unchecked HTML checkbox submits nothing),
    so validated_data can contain has_header_row=False even when the
    caller never sent it at all -- which would wrongly override
    parse_csv()'s own True default. Only trust it if the raw request
    actually contained the key.
    """
    if not validated_data.get("date_column"):
        return None
    extracted = {
        field: validated_data[field]
        for field in _INLINE_MAPPING_FIELDS
        if field in validated_data and field != "has_header_row"
    }
    if "has_header_row" in raw_data:
        extracted["has_header_row"] = validated_data.get("has_header_row", True)
    return extracted


class ImportPreviewView(APIView):
    permission_classes = [HasEntityRole(EntityRole.EDITOR)]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = ImportPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        column_mapping = data.get("column_mapping") or _extract_inline_mapping_data(
            request.data, data
        )
        result = parse_preview(
            account=data["account"],
            file_format=data["file_format"],
            file_bytes=data["file"].read(),
            column_mapping=column_mapping,
        )
        return Response(ImportPreviewResponseSerializer(result).data)


class ImportConfirmView(APIView):
    permission_classes = [HasEntityRole(EntityRole.EDITOR)]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = ImportConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            batch = confirm_import(
                account=data["account"],
                file_format=data["file_format"],
                file_bytes=data["file"].read(),
                original_filename=data["file"].name,
                imported_by=request.user,
                column_mapping=data.get("column_mapping"),
                inline_mapping_data=_extract_inline_mapping_data(request.data, data),
                save_mapping_as=data.get("save_mapping_as") or None,
            )
        except ImportError_ as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc

        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class ImportedTransactionViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = ImportedTransactionSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = ImportedTransaction.objects.accessible_by(self.request.user).select_related(
            "account", "matched_line", "created_entry"
        )
        account_id = self.request.query_params.get("account")
        if account_id:
            qs = qs.filter(account_id=account_id)
        return qs

    def get_permissions(self):
        if self.action in ("confirm_match", "create_entry", "ignore"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    @action(detail=True, methods=["get"], url_path="candidate-matches")
    def candidate_matches(self, request, pk=None):
        imported = self.get_object()
        candidates = find_candidate_matches(imported)
        return Response(JournalLineReadSerializer(candidates, many=True).data)

    @action(detail=True, methods=["post"], url_path="confirm-match")
    def confirm_match_action(self, request, pk=None):
        imported = self.get_object()
        serializer = ConfirmMatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = confirm_match(
                imported_transaction=imported,
                journal_line=serializer.validated_data["journal_line"],
                matched_by=request.user,
            )
        except ImportError_ as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(ImportedTransactionSerializer(updated).data)

    @action(detail=True, methods=["post"], url_path="create-entry")
    def create_entry_action(self, request, pk=None):
        imported = self.get_object()
        serializer = CreateEntryFromImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = create_entry_from_import(
                imported_transaction=imported,
                offsetting_account=serializer.validated_data["offsetting_account"],
                created_by=request.user,
                description=serializer.validated_data.get("description") or None,
            )
        except (ImportError_, LedgerError) as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(ImportedTransactionSerializer(updated).data)

    @action(detail=True, methods=["post"])
    def ignore(self, request, pk=None):
        imported = self.get_object()
        try:
            updated = ignore_imported_transaction(imported_transaction=imported)
        except ImportError_ as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(ImportedTransactionSerializer(updated).data)


class AccountReconciliationRecordsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def _get_account(self, request, account_id):
        account = Account.objects.accessible_by(request.user).filter(pk=account_id).first()
        if account is None:
            from django.http import Http404

            raise Http404
        return account

    def get(self, request, account_id):
        account = self._get_account(request, account_id)
        self.check_object_permissions(request, account)
        records = account.reconciliation_records.all()
        return Response(ReconciliationRecordSerializer(records, many=True).data)

    def post(self, request, account_id):
        account = self._get_account(request, account_id)
        self.check_object_permissions(request, account)
        serializer = ReconciliationRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = mark_account_reconciled(
            account=account,
            statement_date=serializer.validated_data["statement_date"],
            statement_balance=serializer.validated_data["statement_balance"],
            reconciled_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(
            ReconciliationRecordSerializer(record).data, status=status.HTTP_201_CREATED
        )
