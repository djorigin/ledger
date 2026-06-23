from django.http import Http404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.api.permissions import HasEntityRole
from apps.api.serializers.inventory import (
    InventoryCategorySummarySerializer,
    InventoryItemSerializer,
    InventorySummaryQuerySerializer,
)
from apps.entities.models import Entity, EntityRole
from apps.inventory.models import InventoryItem
from apps.inventory.services import compute_inventory_summary


class InventoryItemViewSet(viewsets.ModelViewSet):
    """Standalone -- no GL linkage, same as AssetClass. multipart/form-data
    supported natively via MultiPartParser for the photo upload."""

    serializer_class = InventoryItemSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = InventoryItem.objects.accessible_by(self.request.user).select_related("entity")
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        if self.action == "summary":
            return [HasEntityRole(EntityRole.VIEWER)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}

    @action(detail=False, methods=["get"])
    def summary(self, request):
        query = InventorySummaryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        entity = Entity.objects.accessible_by(request.user).filter(
            pk=query.validated_data["entity"]
        ).first()
        if entity is None:
            raise Http404
        self.check_object_permissions(request, entity)

        summary = compute_inventory_summary(entity)
        data = [
            {
                "category": row.category,
                "total_replacement_value": row.total_replacement_value,
                "item_count": row.item_count,
            }
            for row in summary
        ]
        return Response(InventoryCategorySummarySerializer(data, many=True).data)
