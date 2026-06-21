from rest_framework import serializers

from apps.ap_ar.exceptions import ApArError
from apps.ap_ar.models import Bill, BillPayment, Invoice, InvoicePayment
from apps.ap_ar.services import record_bill, record_invoice
from apps.api.fields import MoneyField
from apps.entities.models import Entity
from apps.ledger.models import Account


class BillPaymentReadSerializer(serializers.ModelSerializer):
    amount = MoneyField()

    class Meta:
        model = BillPayment
        fields = ["id", "payment_date", "amount", "payment_account", "journal_entry", "created_at"]
        read_only_fields = fields


class BillPaymentWriteSerializer(serializers.Serializer):
    payment_date = serializers.DateField()
    amount = MoneyField()
    payment_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())


class BillSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    expense_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    payable_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    amount = MoneyField()
    created_by = serializers.StringRelatedField(read_only=True)
    payments = BillPaymentReadSerializer(many=True, read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id", "entity", "vendor_name", "description", "bill_date", "due_date",
            "amount", "currency", "expense_account", "payable_account",
            "journal_entry", "is_cancelled", "payments",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "journal_entry", "is_cancelled", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return record_bill(created_by=request.user, **validated_data)
        except ApArError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc


class BillProgressSerializer(serializers.Serializer):
    amount = MoneyField()
    amount_paid = MoneyField()
    amount_due = MoneyField()
    status = serializers.CharField()
    is_overdue = serializers.BooleanField()


class InvoicePaymentReadSerializer(serializers.ModelSerializer):
    amount = MoneyField()

    class Meta:
        model = InvoicePayment
        fields = ["id", "payment_date", "amount", "payment_account", "journal_entry", "created_at"]
        read_only_fields = fields


class InvoicePaymentWriteSerializer(serializers.Serializer):
    payment_date = serializers.DateField()
    amount = MoneyField()
    payment_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())


class InvoiceSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    income_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    receivable_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    amount = MoneyField()
    created_by = serializers.StringRelatedField(read_only=True)
    payments = InvoicePaymentReadSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "entity", "customer_name", "description", "invoice_date", "due_date",
            "amount", "currency", "income_account", "receivable_account",
            "journal_entry", "is_cancelled", "payments",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "journal_entry", "is_cancelled", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return record_invoice(created_by=request.user, **validated_data)
        except ApArError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc


class InvoiceProgressSerializer(serializers.Serializer):
    amount = MoneyField()
    amount_paid = MoneyField()
    amount_due = MoneyField()
    status = serializers.CharField()
    is_overdue = serializers.BooleanField()
