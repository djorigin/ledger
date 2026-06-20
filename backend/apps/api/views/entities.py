from rest_framework import viewsets

from apps.api.permissions import HasEntityRole
from apps.api.serializers.entities import EntitySerializer
from apps.entities.models import Entity, EntityRole


class EntityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EntitySerializer
    permission_classes = [HasEntityRole(EntityRole.VIEWER)]

    def get_queryset(self):
        return Entity.objects.accessible_by(self.request.user)
