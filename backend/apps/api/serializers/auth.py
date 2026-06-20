from rest_framework import serializers

from apps.entities.models import EntityMembership


class MembershipSerializer(serializers.ModelSerializer):
    entity_id = serializers.UUIDField(source="entity.id", read_only=True)
    entity_name = serializers.CharField(source="entity.name", read_only=True)

    class Meta:
        model = EntityMembership
        fields = ["entity_id", "entity_name", "role"]


class MeSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    memberships = serializers.SerializerMethodField()

    def get_memberships(self, user):
        qs = EntityMembership.objects.filter(user=user).select_related("entity")
        return MembershipSerializer(qs, many=True).data
