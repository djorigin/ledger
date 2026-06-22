class RecurringError(Exception):
    """Base exception for apps.recurring."""


class AlreadyReviewedError(RecurringError):
    pass
