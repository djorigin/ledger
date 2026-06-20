from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.api.permissions import HasEntityRole
from apps.api.serializers.ledger import (
    AccountSerializer,
    JournalEntryReverseSerializer,
    JournalEntrySerializer,
)
from apps.entities.models import EntityRole
from apps.ledger.exceptions import LedgerError
from apps.ledger.models import Account, JournalEntry
from apps.ledger.services import reverse_journal_entry


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [HasEntityRole(EntityRole.VIEWER)]

    def get_queryset(self):
        return Account.objects.accessible_by(self.request.user).select_related("entity", "parent")


class JournalEntryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = JournalEntrySerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return (
            JournalEntry.objects.accessible_by(self.request.user)
            .select_related("entity", "created_by", "updated_by", "reverses")
            .prefetch_related("lines__account")
        )

    def get_permissions(self):
        if self.action in ("create", "reverse"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        entry = self.get_object()
        serializer = JournalEntryReverseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reversal = reverse_journal_entry(
                entry=entry,
                reversed_by_user=request.user,
                reversal_date=serializer.validated_data.get("reversal_date"),
            )
        except LedgerError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(
            JournalEntrySerializer(reversal, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
