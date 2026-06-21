from datetime import date

import strawberry

from apps.api.graphql.types import (
    AccountType,
    BudgetType,
    EntityType,
    JournalEntryType,
    MeType,
    ProjectType,
    SavingsGoalType,
)
from apps.budgets.models import Budget, Project, SavingsGoal
from apps.entities.models import Entity
from apps.ledger.models import Account, JournalEntry


def _require_user(info: strawberry.types.Info):
    user = info.context.request.user
    if not user.is_authenticated:
        raise Exception("Authentication required.")
    return user


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: strawberry.types.Info) -> MeType:
        user = _require_user(info)
        return MeType.from_model(user)

    @strawberry.field
    def entities(self, info: strawberry.types.Info) -> list[EntityType]:
        user = _require_user(info)
        return [EntityType.from_model(e) for e in Entity.objects.accessible_by(user)]

    @strawberry.field
    def accounts(self, info: strawberry.types.Info, entity: strawberry.ID | None = None) -> list[AccountType]:
        user = _require_user(info)
        qs = Account.objects.accessible_by(user).select_related("entity", "parent")
        if entity is not None:
            qs = qs.filter(entity_id=entity)
        return [AccountType.from_model(a) for a in qs]

    @strawberry.field
    def journal_entries(
        self,
        info: strawberry.types.Info,
        entity: strawberry.ID,
        account: strawberry.ID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[JournalEntryType]:
        user = _require_user(info)
        qs = (
            JournalEntry.objects.accessible_by(user)
            .filter(entity_id=entity)
            .prefetch_related("lines__account")
        )
        if account is not None:
            qs = qs.filter(lines__account_id=account).distinct()
        if date_from is not None:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to is not None:
            qs = qs.filter(entry_date__lte=date_to)
        return [JournalEntryType.from_model(e) for e in qs]

    @strawberry.field
    def budgets(self, info: strawberry.types.Info, entity: strawberry.ID) -> list[BudgetType]:
        user = _require_user(info)
        qs = Budget.objects.accessible_by(user).filter(entity_id=entity).select_related("account")
        return [BudgetType.from_model(b) for b in qs]

    @strawberry.field
    def savings_goals(self, info: strawberry.types.Info, entity: strawberry.ID) -> list[SavingsGoalType]:
        user = _require_user(info)
        qs = SavingsGoal.objects.accessible_by(user).filter(entity_id=entity)
        return [SavingsGoalType.from_model(g) for g in qs]

    @strawberry.field
    def projects(self, info: strawberry.types.Info, entity: strawberry.ID) -> list[ProjectType]:
        user = _require_user(info)
        qs = Project.objects.accessible_by(user).filter(entity_id=entity)
        return [ProjectType.from_model(p) for p in qs]
