from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entities.models import Entity, EntityMembership, EntityRole, EntityType
from apps.users.models import User


class Command(BaseCommand):
    help = "Seed local dev DB with a sample family, entities, and memberships."

    @transaction.atomic
    def handle(self, *args, **options):
        alice, _ = User.objects.get_or_create(
            email="alice@example.com", defaults={"first_name": "Alice"}
        )
        alice.set_password("devpass123")
        alice.save()

        bob, _ = User.objects.get_or_create(
            email="bob@example.com", defaults={"first_name": "Bob"}
        )
        bob.set_password("devpass123")
        bob.save()

        household, _ = Entity.objects.get_or_create(
            name="Smith Household", type=EntityType.HOUSEHOLD
        )
        business, _ = Entity.objects.get_or_create(
            name="Freelance Co", type=EntityType.BUSINESS
        )

        EntityMembership.objects.get_or_create(
            user=alice, entity=household, defaults={"role": EntityRole.OWNER}
        )
        EntityMembership.objects.get_or_create(
            user=bob, entity=household, defaults={"role": EntityRole.EDITOR}
        )
        EntityMembership.objects.get_or_create(
            user=alice, entity=business, defaults={"role": EntityRole.VIEWER}
        )
        EntityMembership.objects.get_or_create(
            user=bob, entity=business, defaults={"role": EntityRole.OWNER}
        )

        self.stdout.write(self.style.SUCCESS("Seeded demo users, entities, and memberships."))
