from django.http import Http404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.api.permissions import HasEntityRole
from apps.api.serializers.payroll import (
    PayslipSerializer,
    PayslipSummaryQuerySerializer,
    PayslipSummarySerializer,
)
from apps.entities.models import Entity, EntityRole
from apps.payroll.models import Payslip
from apps.payroll.services import compute_payslip_summary


class PayslipViewSet(viewsets.ModelViewSet):
    """
    No DELETE -- a payslip is a financial record like Bill/Invoice, never
    hard-deleted. Unlike Bill/Invoice (which disallow editing entirely and
    require an explicit cancel action), update here is allowed: PUT/PATCH
    routes through PayslipSerializer.update() -> update_payslip(), which
    reverses the existing journal entry and posts a fresh one rather than
    mutating a posted entry in place -- the correction mechanism the brief
    explicitly asked for.
    """

    serializer_class = PayslipSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        qs = Payslip.objects.accessible_by(self.request.user).select_related("entity", "journal_entry")
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        period_start = self.request.query_params.get("period_start")
        if period_start:
            qs = qs.filter(payment_date__gte=period_start)
        period_end = self.request.query_params.get("period_end")
        if period_end:
            qs = qs.filter(payment_date__lte=period_end)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    @action(detail=False, methods=["get"])
    def summary(self, request):
        query = PayslipSummaryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        entity = Entity.objects.accessible_by(request.user).filter(
            pk=query.validated_data["entity"]
        ).first()
        if entity is None:
            raise Http404
        self.check_object_permissions(request, entity)

        payslips = Payslip.objects.filter(entity=entity)
        period_start = query.validated_data.get("period_start")
        if period_start:
            payslips = payslips.filter(payment_date__gte=period_start)
        period_end = query.validated_data.get("period_end")
        if period_end:
            payslips = payslips.filter(payment_date__lte=period_end)

        summary = compute_payslip_summary(payslips)
        data = {"gross": summary.gross, "tax": summary.tax, "net": summary.net, "count": summary.count}
        return Response(PayslipSummarySerializer(data).data)
