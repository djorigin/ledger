from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ParsedRow:
    """
    Format-agnostic shape both parsers (CSV, OFX) produce. Downstream
    import/matching/posting logic consumes only this -- it never branches
    on which source format a row came from.

    external_id is populated by the OFX parser directly (the format's own
    FITID) but left blank by the CSV parser -- CSV has no native unique id,
    so the service layer computes a synthesized hash once it knows which
    account the rows belong to (the parser itself has no DB/account
    knowledge, by design).
    """

    transaction_date: date
    description: str
    amount: Decimal
    memo: str = ""
    running_balance: Decimal | None = None
    external_id: str = ""
    raw_row: dict = field(default_factory=dict)
