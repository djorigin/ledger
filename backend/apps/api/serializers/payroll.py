from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.entities.models import Entity
from apps.ledger.models import Account
from apps.payroll.models import Payslip
from apps.payroll.services import record_payslip, update_payslip


def _reraise_as_drf_error(exc: DjangoValidationError):
    detail = exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
    raise serializers.ValidationError(detail) from exc


class PayslipSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    income_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    pretax_lease_expense_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    tax_expense_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    fuel_card_expense_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    social_club_expense_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    cfmeu_expense_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    bank_account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())

    gross_amount = MoneyField()
    deduction_tax = MoneyField(required=False)
    deduction_fuel_card = MoneyField(required=False)
    deduction_social_club = MoneyField(required=False)
    deduction_cfmeu = MoneyField(required=False)
    deduction_pretax_lease = MoneyField(required=False)
    net_pay = MoneyField()

    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payslip
        fields = [
            "id", "entity", "pay_period_start", "pay_period_end", "payment_date", "currency",
            "gross_amount", "deduction_tax", "deduction_fuel_card", "deduction_social_club",
            "deduction_cfmeu", "deduction_pretax_lease", "net_pay",
            "income_account", "pretax_lease_expense_account", "tax_expense_account",
            "fuel_card_expense_account", "social_club_expense_account", "cfmeu_expense_account",
            "bank_account", "journal_entry", "notes",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "journal_entry", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return record_payslip(created_by=request.user, **validated_data)
        except DjangoValidationError as exc:
            _reraise_as_drf_error(exc)

    def update(self, instance, validated_data):
        request = self.context["request"]
        try:
            return update_payslip(payslip=instance, updated_by=request.user, **validated_data)
        except DjangoValidationError as exc:
            _reraise_as_drf_error(exc)


class PayslipSummarySerializer(serializers.Serializer):
    gross = MoneyField()
    tax = MoneyField()
    net = MoneyField()
    count = serializers.IntegerField()


class PayslipSummaryQuerySerializer(serializers.Serializer):
    entity = serializers.UUIDField()
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
