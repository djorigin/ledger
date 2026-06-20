from django.db import models


class ImportedTransactionQuerySet(models.QuerySet):
    def accessible_by(self, user):
        from apps.entities.models import Entity

        return self.filter(account__entity__in=Entity.objects.accessible_by(user))


class ImportBatchQuerySet(models.QuerySet):
    def accessible_by(self, user):
        from apps.entities.models import Entity

        return self.filter(account__entity__in=Entity.objects.accessible_by(user))


class ColumnMappingQuerySet(models.QuerySet):
    def accessible_by(self, user):
        from apps.entities.models import Entity

        return self.filter(account__entity__in=Entity.objects.accessible_by(user))
