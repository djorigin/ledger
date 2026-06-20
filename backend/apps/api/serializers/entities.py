from rest_framework import serializers

from apps.entities.models import Entity


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = ["id", "name", "type", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = fields
