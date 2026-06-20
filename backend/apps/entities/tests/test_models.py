import pytest

from apps.entities.models import Entity, EntityMembership, EntityRole, EntityType
from apps.entities.permissions import can_edit, can_view, is_owner
from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_membership_role_grants_access():
    owner = User.objects.create_user(email="owner@example.com", password="x")
    viewer = User.objects.create_user(email="viewer@example.com", password="x")
    entity = Entity.objects.create(name="Household", type=EntityType.HOUSEHOLD)
    EntityMembership.objects.create(user=owner, entity=entity, role=EntityRole.OWNER)
    EntityMembership.objects.create(user=viewer, entity=entity, role=EntityRole.VIEWER)

    assert is_owner(owner, entity)
    assert can_edit(owner, entity)
    assert can_view(viewer, entity)
    assert not can_edit(viewer, entity)


def test_accessible_by_filters_to_membership():
    user = User.objects.create_user(email="u@example.com", password="x")
    mine = Entity.objects.create(name="Mine", type=EntityType.HOUSEHOLD)
    other = Entity.objects.create(name="Other", type=EntityType.BUSINESS)
    EntityMembership.objects.create(user=user, entity=mine, role=EntityRole.EDITOR)

    accessible = Entity.objects.accessible_by(user)
    assert mine in accessible
    assert other not in accessible


def test_user_can_have_different_roles_on_different_entities():
    user = User.objects.create_user(email="multi@example.com", password="x")
    entity_a = Entity.objects.create(name="A", type=EntityType.HOUSEHOLD)
    entity_b = Entity.objects.create(name="B", type=EntityType.BUSINESS)
    EntityMembership.objects.create(user=user, entity=entity_a, role=EntityRole.OWNER)
    EntityMembership.objects.create(user=user, entity=entity_b, role=EntityRole.VIEWER)

    assert is_owner(user, entity_a)
    assert can_view(user, entity_b)
    assert not can_edit(user, entity_b)
