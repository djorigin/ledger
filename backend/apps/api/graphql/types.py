from datetime import date as date_

import strawberry

from apps.api.graphql.scalars import DecimalScalar


@strawberry.type
class EntityType:
    id: strawberry.ID
    name: str
    type: str
    description: str
    is_active: bool

    @classmethod
    def from_model(cls, entity):
        return cls(
            id=strawberry.ID(str(entity.id)),
            name=entity.name,
            type=entity.type,
            description=entity.description,
            is_active=entity.is_active,
        )


@strawberry.type
class AccountType:
    id: strawberry.ID
    entity_id: strawberry.ID
    parent_id: strawberry.ID | None
    account_type: str
    name: str
    code: str
    native_currency: str
    is_active: bool
    is_cash_equivalent: bool

    @classmethod
    def from_model(cls, account):
        return cls(
            id=strawberry.ID(str(account.id)),
            entity_id=strawberry.ID(str(account.entity_id)),
            parent_id=strawberry.ID(str(account.parent_id)) if account.parent_id else None,
            account_type=account.account_type,
            name=account.name,
            code=account.code,
            native_currency=account.native_currency,
            is_active=account.is_active,
            is_cash_equivalent=account.is_cash_equivalent,
        )


@strawberry.type
class JournalLineType:
    id: strawberry.ID
    account_id: strawberry.ID
    debit_amount: DecimalScalar
    credit_amount: DecimalScalar
    currency: str
    description: str

    @classmethod
    def from_model(cls, line):
        return cls(
            id=strawberry.ID(str(line.id)),
            account_id=strawberry.ID(str(line.account_id)),
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            currency=line.currency,
            description=line.description,
        )


@strawberry.type
class JournalEntryType:
    id: strawberry.ID
    entity_id: strawberry.ID
    entry_date: date_
    description: str
    status: str
    project_id: strawberry.ID | None
    lines: list[JournalLineType]

    @classmethod
    def from_model(cls, entry):
        return cls(
            id=strawberry.ID(str(entry.id)),
            entity_id=strawberry.ID(str(entry.entity_id)),
            entry_date=entry.entry_date,
            description=entry.description,
            status=entry.status,
            project_id=strawberry.ID(str(entry.project_id)) if entry.project_id else None,
            lines=[JournalLineType.from_model(line) for line in entry.lines.all()],
        )


@strawberry.type
class BudgetType:
    id: strawberry.ID
    entity_id: strawberry.ID
    account_id: strawberry.ID
    name: str
    period_type: str
    period_start: date_
    period_end: date_
    budgeted_amount: DecimalScalar
    include_descendants: bool

    @classmethod
    def from_model(cls, budget):
        return cls(
            id=strawberry.ID(str(budget.id)),
            entity_id=strawberry.ID(str(budget.entity_id)),
            account_id=strawberry.ID(str(budget.account_id)),
            name=budget.name,
            period_type=budget.period_type,
            period_start=budget.period_start,
            period_end=budget.period_end,
            budgeted_amount=budget.budgeted_amount,
            include_descendants=budget.include_descendants,
        )


@strawberry.type
class SavingsGoalType:
    id: strawberry.ID
    entity_id: strawberry.ID
    name: str
    target_amount: DecimalScalar
    target_date: date_
    linked_account_id: strawberry.ID

    @classmethod
    def from_model(cls, goal):
        return cls(
            id=strawberry.ID(str(goal.id)),
            entity_id=strawberry.ID(str(goal.entity_id)),
            name=goal.name,
            target_amount=goal.target_amount,
            target_date=goal.target_date,
            linked_account_id=strawberry.ID(str(goal.linked_account_id)),
        )


@strawberry.type
class ProjectType:
    id: strawberry.ID
    entity_id: strawberry.ID
    name: str
    description: str
    budget_amount: DecimalScalar
    currency: str
    status: str

    @classmethod
    def from_model(cls, project):
        return cls(
            id=strawberry.ID(str(project.id)),
            entity_id=strawberry.ID(str(project.entity_id)),
            name=project.name,
            description=project.description,
            budget_amount=project.budget_amount,
            currency=project.currency,
            status=project.status,
        )


@strawberry.type
class MembershipType:
    entity_id: strawberry.ID
    entity_name: str
    role: str


@strawberry.type
class MeType:
    id: strawberry.ID
    email: str
    first_name: str
    last_name: str
    is_superuser: bool
    memberships: list[MembershipType]

    @classmethod
    def from_model(cls, user):
        from apps.entities.models import EntityMembership

        memberships = EntityMembership.objects.filter(user=user).select_related("entity")
        return cls(
            id=strawberry.ID(str(user.id)),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_superuser=user.is_superuser,
            memberships=[
                MembershipType(
                    entity_id=strawberry.ID(str(m.entity_id)), entity_name=m.entity.name, role=m.role
                )
                for m in memberships
            ],
        )
