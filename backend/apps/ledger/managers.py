from django.db import models


class AccountQuerySet(models.QuerySet):
    def accessible_by(self, user):
        from apps.entities.models import Entity

        return self.filter(entity__in=Entity.objects.accessible_by(user))

    def with_role_at_least(self, user, minimum_role):
        from apps.entities.models import Entity

        return self.filter(entity__in=Entity.objects.with_role_at_least(user, minimum_role))


class JournalEntryQuerySet(models.QuerySet):
    def accessible_by(self, user):
        from apps.entities.models import Entity

        return self.filter(entity__in=Entity.objects.accessible_by(user))

    def with_role_at_least(self, user, minimum_role):
        from apps.entities.models import Entity

        return self.filter(entity__in=Entity.objects.with_role_at_least(user, minimum_role))
