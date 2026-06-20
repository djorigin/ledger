from django.db import models


class EntityQuerySet(models.QuerySet):
    def accessible_by(self, user):
        """Entities the given user has any membership role on (or all, if superuser)."""
        if user and user.is_authenticated and user.is_superuser:
            return self
        if not user or not user.is_authenticated:
            return self.none()
        return self.filter(memberships__user=user).distinct()

    def with_role_at_least(self, user, minimum_role):
        from apps.entities.permissions import ROLE_HIERARCHY

        if user and user.is_authenticated and user.is_superuser:
            return self
        if not user or not user.is_authenticated:
            return self.none()
        allowed_roles = ROLE_HIERARCHY.get(minimum_role, set())
        return self.filter(
            memberships__user=user, memberships__role__in=allowed_roles
        ).distinct()
