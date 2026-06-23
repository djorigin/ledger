from rest_framework import serializers

from apps.api.fields import MoneyField
from apps.entities.models import Entity
from apps.inventory.models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    entity = serializers.PrimaryKeyRelatedField(queryset=Entity.objects.all())
    purchase_price = MoneyField(required=False, allow_null=True)
    estimated_replacement_value = MoneyField(required=False, allow_null=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id", "entity", "name", "category", "description", "brand", "model_number",
            "serial_number", "location", "purchase_date", "purchase_price",
            "estimated_replacement_value", "currency", "insured", "insurer", "policy_number",
            "photo", "notes", "is_active",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        # DRF's BooleanField treats a key absent from multipart/form-data
        # as an unchecked HTML checkbox -- i.e. False -- regardless of the
        # model's own default=True, on any *non-partial* write (PATCH is
        # unaffected; this is specifically the create/full-PUT path).
        # Photo uploads are always multipart, so silently creating
        # deactivated items the moment "is_active" is merely omitted (the
        # overwhelmingly common case) would be a footgun. There's no
        # legitimate "create as inactive" use case, so this is forced
        # rather than documented-and-hoped-for from every client.
        validated_data["is_active"] = True
        return super().create(validated_data)


class InventoryCategorySummarySerializer(serializers.Serializer):
    category = serializers.CharField()
    total_replacement_value = MoneyField()
    item_count = serializers.IntegerField()


class InventorySummaryQuerySerializer(serializers.Serializer):
    entity = serializers.UUIDField()
