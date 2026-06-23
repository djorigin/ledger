from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.assets.models import AssetClass, AssetValuation
from apps.entities.models import Entity
from apps.ledger.constants import validate_currency_code


class AssetValuationReadSerializer(serializers.ModelSerializer):
    current_value = MoneyField()

    class Meta:
        model = AssetValuation
        fields = ["id", "valuation_date", "current_value", "currency", "source", "notes", "created_at"]
        read_only_fields = fields


class AssetValuationWriteSerializer(serializers.Serializer):
    valuation_date = serializers.DateField()
    current_value = MoneyField()
    currency = serializers.CharField(max_length=3, validators=[validate_currency_code])
    source = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AssetClassSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    acquisition_cost = MoneyField(required=False, allow_null=True)
    created_by = serializers.StringRelatedField(read_only=True)
    latest_valuation = AssetValuationReadSerializer(read_only=True)
    valuations = AssetValuationReadSerializer(many=True, read_only=True)

    class Meta:
        model = AssetClass
        fields = [
            "id", "entity", "name", "category", "description",
            "acquisition_date", "acquisition_cost", "currency", "is_active", "notes",
            "latest_valuation", "valuations",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class AssetClassValueSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    asset_name = serializers.CharField()
    entity_id = serializers.UUIDField()
    value = MoneyField()
    as_of = serializers.DateField(allow_null=True)


class AssetRegisterNetWorthQuerySerializer(serializers.Serializer):
    reporting_currency = serializers.CharField(validators=[validate_currency_code])


class AssetRegisterNetWorthSerializer(serializers.Serializer):
    reporting_currency = serializers.CharField()
    rows = AssetClassValueSerializer(many=True)
    total = MoneyField()
