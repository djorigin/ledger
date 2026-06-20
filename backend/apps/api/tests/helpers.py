from rest_framework.test import APIClient

from apps.entities.models import Entity, EntityMembership, EntityType
from apps.ledger.models import Account, AccountType
from apps.users.models import User


def make_user(email="u@example.com"):
    return User.objects.create_user(email=email, password="testpass123")


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_membership(user, entity, role):
    return EntityMembership.objects.create(user=user, entity=entity, role=role)


def make_accounts(entity, currency="AUD"):
    bank = Account.objects.create(
        entity=entity, account_type=AccountType.ASSET, name="Bank", native_currency=currency
    )
    groceries = Account.objects.create(
        entity=entity, account_type=AccountType.EXPENSE, name="Groceries", native_currency=currency
    )
    return bank, groceries


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client
