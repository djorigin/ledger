class LedgerError(Exception):
    """Base class for all apps.ledger domain errors."""


class UnbalancedJournalEntryError(LedgerError):
    pass


class InvalidJournalLineError(LedgerError):
    pass


class CurrencyMismatchError(InvalidJournalLineError):
    pass


class CrossEntityAccountError(InvalidJournalLineError):
    pass


class JournalEntryImmutableError(LedgerError):
    """Raised when code attempts to hard-delete a posted/reversed JournalEntry."""


class JournalEntryAlreadyReversedError(LedgerError):
    pass
