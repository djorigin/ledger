from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.api.permissions import HasEntityRole
from apps.api.serializers.recurring import (
    ApprovePendingEntrySerializer,
    PendingRecurringEntrySerializer,
    RecurringTransactionTemplateSerializer,
)
from apps.entities.models import EntityRole
from apps.recurring.exceptions import RecurringError
from apps.recurring.models import PendingRecurringEntry, RecurringTransactionTemplate
from apps.recurring.services import approve_pending_entry, dismiss_pending_entry


class RecurringTransactionTemplateViewSet(viewsets.ModelViewSet):
    """
    Full ModelViewSet -- a template is an editable setting, not a
    financial transaction itself (unlike Bill/JournalEntry), so it has no
    immutability constraint. Editing/deleting a template never touches an
    already-posted JournalEntry.
    """

    serializer_class = RecurringTransactionTemplateSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = RecurringTransactionTemplate.objects.accessible_by(self.request.user).select_related(
            "entity", "debit_account", "credit_account"
        )
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PendingRecurringEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """Entries are system-generated only -- never created/edited directly
    via the API, only approved or dismissed."""

    serializer_class = PendingRecurringEntrySerializer

    def get_queryset(self):
        qs = PendingRecurringEntry.objects.accessible_by(self.request.user).select_related(
            "template", "journal_entry", "reviewed_by"
        )
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(template__entity_id=entity_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def get_permissions(self):
        if self.action in ("approve", "dismiss"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        pending_entry = self.get_object()
        serializer = ApprovePendingEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            pending_entry = approve_pending_entry(
                pending_entry=pending_entry,
                approved_by=request.user,
                amount=serializer.validated_data.get("amount"),
            )
        except RecurringError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(PendingRecurringEntrySerializer(pending_entry).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        pending_entry = self.get_object()
        try:
            pending_entry = dismiss_pending_entry(pending_entry=pending_entry, dismissed_by=request.user)
        except RecurringError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(PendingRecurringEntrySerializer(pending_entry).data)
