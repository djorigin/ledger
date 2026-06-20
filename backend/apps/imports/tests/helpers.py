from apps.entities.models import Entity, EntityType
from apps.imports.models import ImportBatch, ImportFileFormat
from apps.ledger.models import Account, AccountType
from apps.users.models import User


def make_user(email="u@example.com"):
    return User.objects.create_user(email=email, password="x")


def make_entity(name="Household"):
    return Entity.objects.create(name=name, type=EntityType.HOUSEHOLD)


def make_account(entity, name="Bank", account_type=AccountType.ASSET, currency="AUD"):
    return Account.objects.create(
        entity=entity, account_type=account_type, name=name, native_currency=currency
    )


def make_import_batch(account, imported_by, file_format=ImportFileFormat.CSV):
    return ImportBatch.objects.create(
        account=account,
        file_format=file_format,
        original_filename="statement.csv",
        imported_by=imported_by,
    )
