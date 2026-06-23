from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.api.permissions import HasEntityRole
from apps.api.serializers.assets import (
    AssetClassSerializer,
    AssetRegisterNetWorthQuerySerializer,
    AssetRegisterNetWorthSerializer,
    AssetValuationReadSerializer,
    AssetValuationWriteSerializer,
)
from apps.assets.models import AssetClass
from apps.assets.services import compute_asset_register_net_worth
from apps.entities.models import Entity, EntityRole


class AssetClassViewSet(viewsets.ModelViewSet):
    """
    Standalone tracking -- no FK into apps.ledger at all. Full ModelViewSet
    (unlike Bill/Invoice, an AssetClass isn't a financial transaction
    itself, so ordinary edit/delete is safe).
    """

    serializer_class = AssetClassSerializer

    def get_queryset(self):
        qs = AssetClass.objects.accessible_by(self.request.user).select_related("entity").prefetch_related(
            "valuations"
        )
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        if self.action == "valuations" and self.request.method == "POST":
            return [HasEntityRole(EntityRole.EDITOR)()]
        if self.action == "net_worth_summary":
            # Spans every accessible entity, like NetWorthView -- no single
            # entity to check HasEntityRole against; the accessible_by(user)
            # queryset inside compute_asset_register_net_worth is the
            # access boundary, same precedent as apps/api/views/reports.py.
            return [IsAuthenticated()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get", "post"])
    def valuations(self, request, pk=None):
        asset = self.get_object()
        if request.method == "GET":
            return Response(
                AssetValuationReadSerializer(asset.valuations.all(), many=True).data
            )

        serializer = AssetValuationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valuation = asset.valuations.create(created_by=request.user, **serializer.validated_data)
        return Response(AssetValuationReadSerializer(valuation).data, status=201)

    @action(detail=False, methods=["get"], url_path="net-worth-summary")
    def net_worth_summary(self, request):
        query = AssetRegisterNetWorthQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        entities = Entity.objects.accessible_by(request.user)
        report = compute_asset_register_net_worth(
            entities, reporting_currency=query.validated_data["reporting_currency"]
        )
        data = {
            "reporting_currency": report.reporting_currency,
            "rows": [
                {
                    "asset_id": row.asset.id,
                    "asset_name": row.asset.name,
                    "entity_id": row.asset.entity_id,
                    "value": row.value,
                    "as_of": row.as_of,
                }
                for row in report.rows
            ],
            "total": report.total,
        }
        return Response(AssetRegisterNetWorthSerializer(data).data)
