from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ap_ar.exceptions import ApArError
from apps.ap_ar.models import Bill, Invoice
from apps.ap_ar.services import (
    cancel_bill,
    cancel_invoice,
    compute_bill_progress,
    compute_invoice_progress,
    record_bill_payment,
    record_invoice_payment,
)
from apps.api.serializers.ap_ar import (
    BillPaymentReadSerializer,
    BillPaymentWriteSerializer,
    BillProgressSerializer,
    BillSerializer,
    InvoicePaymentReadSerializer,
    InvoicePaymentWriteSerializer,
    InvoiceProgressSerializer,
    InvoiceSerializer,
)
from apps.api.permissions import HasEntityRole
from apps.entities.models import EntityRole


class BillViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BillSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = (
            Bill.objects.accessible_by(self.request.user)
            .select_related("entity", "expense_account", "payable_account")
            .prefetch_related("payments")
        )
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "cancel"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        if self.action == "payments" and self.request.method == "POST":
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        bill = self.get_object()
        result = compute_bill_progress(bill)
        return Response(
            BillProgressSerializer(
                {
                    "amount": result.amount,
                    "amount_paid": result.amount_paid,
                    "amount_due": result.amount_due,
                    "status": result.status,
                    "is_overdue": result.is_overdue,
                }
            ).data
        )

    @action(detail=True, methods=["get", "post"])
    def payments(self, request, pk=None):
        bill = self.get_object()
        if request.method == "GET":
            return Response(BillPaymentReadSerializer(bill.payments.all(), many=True).data)

        serializer = BillPaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = record_bill_payment(
                bill=bill, created_by=request.user, **serializer.validated_data
            )
        except ApArError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(BillPaymentReadSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        bill = self.get_object()
        try:
            bill = cancel_bill(bill=bill, cancelled_by=request.user)
        except ApArError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(BillSerializer(bill, context={"request": request}).data)


class InvoiceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InvoiceSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = (
            Invoice.objects.accessible_by(self.request.user)
            .select_related("entity", "income_account", "receivable_account")
            .prefetch_related("payments")
        )
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "cancel"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        if self.action == "payments" and self.request.method == "POST":
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        invoice = self.get_object()
        result = compute_invoice_progress(invoice)
        return Response(
            InvoiceProgressSerializer(
                {
                    "amount": result.amount,
                    "amount_paid": result.amount_paid,
                    "amount_due": result.amount_due,
                    "status": result.status,
                    "is_overdue": result.is_overdue,
                }
            ).data
        )

    @action(detail=True, methods=["get", "post"])
    def payments(self, request, pk=None):
        invoice = self.get_object()
        if request.method == "GET":
            return Response(InvoicePaymentReadSerializer(invoice.payments.all(), many=True).data)

        serializer = InvoicePaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = record_invoice_payment(
                invoice=invoice, created_by=request.user, **serializer.validated_data
            )
        except ApArError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(InvoicePaymentReadSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        try:
            invoice = cancel_invoice(invoice=invoice, cancelled_by=request.user)
        except ApArError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(InvoiceSerializer(invoice, context={"request": request}).data)
