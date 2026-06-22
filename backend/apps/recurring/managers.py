from django.db import models


class RecurringTransactionTemplateQuerySet(models.QuerySet):
    def accessible_by(self, user):
        from apps.entities.models import Entity

        return self.filter(entity__in=Entity.objects.accessible_by(user))

    def with_role_at_least(self, user, minimum_role):
        from apps.entities.models import Entity

        return self.filter(entity__in=Entity.objects.with_role_at_least(user, minimum_role))


class PendingRecurringEntryQuerySet(models.QuerySet):
    def accessible_by(self, user):
        from apps.entities.models import Entity

        return self.filter(template__entity__in=Entity.objects.accessible_by(user))

    def with_role_at_least(self, user, minimum_role):
        from apps.entities.models import Entity

        return self.filter(
            template__entity__in=Entity.objects.with_role_at_least(user, minimum_role)
        )
