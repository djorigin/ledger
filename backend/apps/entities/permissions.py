from apps.entities.models import EntityRole

# Defines which roles satisfy a given minimum-required role.
# OWNER can do anything EDITOR/VIEWER can; EDITOR can do anything VIEWER can.
ROLE_HIERARCHY = {
    EntityRole.VIEWER: {EntityRole.VIEWER, EntityRole.EDITOR, EntityRole.OWNER},
    EntityRole.EDITOR: {EntityRole.EDITOR, EntityRole.OWNER},
    EntityRole.OWNER: {EntityRole.OWNER},
}


def get_role(user, entity):
    """Return the user's EntityRole on this entity, or None if no membership."""
    if not user or not user.is_authenticated:
        return None
    membership = entity.memberships.filter(user=user).only("role").first()
    return membership.role if membership else None


def has_role_at_least(user, entity, minimum_role):
    """True if user's role on entity satisfies minimum_role (or user is superuser)."""
    if user and user.is_authenticated and user.is_superuser:
        return True
    role = get_role(user, entity)
    if role is None:
        return False
    return role in ROLE_HIERARCHY.get(minimum_role, set())


def can_view(user, entity):
    return has_role_at_least(user, entity, EntityRole.VIEWER)


def can_edit(user, entity):
    return has_role_at_least(user, entity, EntityRole.EDITOR)


def is_owner(user, entity):
    return has_role_at_least(user, entity, EntityRole.OWNER)
