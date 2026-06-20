class ImportError_(Exception):
    """Base class for all apps.imports domain errors. Named ImportError_ to
    avoid shadowing the Python builtin ImportError."""


class ColumnMappingError(ImportError_):
    """The supplied column mapping doesn't match the file's actual columns."""


class AlreadyMatchedError(ImportError_):
    """The ImportedTransaction or JournalLine is already linked elsewhere."""


class CrossAccountMatchError(ImportError_):
    """Attempted to match across two different accounts."""
