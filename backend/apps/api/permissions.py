from rest_framework.permissions import BasePermission

from apps.entities.models import Entity
from apps.entities.permissions import has_role_at_least


def _resolve_entity(obj):
    """
    Resolves the relevant Entity for permission checks. An Entity checks
    itself; anything with a direct `.entity` (Account, JournalEntry) uses
    that; anything with only `.account` (ImportedTransaction, ImportBatch,
    ColumnMapping) resolves through the account's entity.
    """
    if isinstance(obj, Entity):
        return obj
    if hasattr(obj, "entity"):
        return obj.entity
    return obj.account.entity


class _HasEntityRole(BasePermission):
    minimum_role = None  # set by the HasEntityRole() factory below

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Viewset actions other than "create" (list/retrieve/custom detail
        # actions): no object yet to check role against for list/create-less
        # actions -- list filtering happens via .accessible_by() in
        # get_queryset(), and retrieve/detail actions are checked by
        # has_object_permission once get_object() runs. Plain APIViews
        # (file upload endpoints) have no `.action` attribute at all and
        # always need target resolution, since there's no list/retrieve
        # concept for them.
        action = getattr(view, "action", None)
        if action is not None and action != "create":
            return True
        return self._check_create_target(request)

    def _check_create_target(self, request):
        entity_id = request.data.get("entity")
        if entity_id:
            entity = Entity.objects.filter(pk=entity_id).first()
            if entity is None:
                # Invalid entity in the payload: let the serializer's own
                # field validation produce the 400, not a 403 here.
                return True
            return has_role_at_least(request.user, entity, self.minimum_role)

        account_id = request.data.get("account")
        if account_id:
            from apps.ledger.models import Account

            account = Account.objects.filter(pk=account_id).first()
            if account is None:
                return True
            return has_role_at_least(request.user, account.entity, self.minimum_role)

        # Neither present: let the serializer's own validation produce a
        # 400, not a 403 here.
        return True

    def has_object_permission(self, request, view, obj):
        entity = _resolve_entity(obj)
        return has_role_at_least(request.user, entity, self.minimum_role)


def HasEntityRole(minimum_role):
    """
    Factory returning a BasePermission subclass pinned to `minimum_role`, so
    it can be used in permission_classes = [HasEntityRole(EntityRole.EDITOR)]
    exactly like any other DRF permission class.
    """
    return type(
        f"HasEntityRole_{minimum_role}",
        (_HasEntityRole,),
        {"minimum_role": minimum_role},
    )
