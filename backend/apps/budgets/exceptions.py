class BudgetsError(Exception):
    """Base class for all apps.budgets domain errors."""


class InvalidProjectionParametersError(BudgetsError):
    pass
