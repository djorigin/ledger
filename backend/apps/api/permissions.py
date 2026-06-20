from rest_framework.permissions import BasePermission

from apps.entities.models import Entity
from apps.entities.permissions import has_role_at_least


def _resolve_entity(obj):
    """An Entity's relevant entity is itself; anything else exposes `.entity`."""
    return obj if isinstance(obj, Entity) else obj.entity


class _HasEntityRole(BasePermission):
    minimum_role = None  # set by the HasEntityRole() factory below

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action != "create":
            # list/retrieve: no object yet to check role against -- list
            # filtering happens via .accessible_by() in get_queryset(), and
            # retrieve is checked by has_object_permission below.
            return True
        return self._check_create_target_entity(request)

    def _check_create_target_entity(self, request):
        entity_id = request.data.get("entity")
        if not entity_id:
            # Missing/invalid entity in the payload: let the serializer's
            # own field validation produce the 400, not a 403 here.
            return True
        entity = Entity.objects.filter(pk=entity_id).first()
        if entity is None:
            return True
        return has_role_at_least(request.user, entity, self.minimum_role)

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
