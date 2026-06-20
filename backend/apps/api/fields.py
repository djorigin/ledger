from rest_framework import serializers


class MoneyField(serializers.DecimalField):
    """
    Money amounts are always Decimal(max_digits=19, decimal_places=4),
    matching JournalLine.debit_amount/credit_amount precision exactly.
    Renders as a JSON string (DecimalField's coerce_to_string=True default,
    deliberately not overridden) so clients never round-trip money through
    a native JSON float.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 19)
        kwargs.setdefault("decimal_places", 4)
        super().__init__(**kwargs)
