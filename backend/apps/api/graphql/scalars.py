from decimal import Decimal
from typing import NewType

import strawberry

# Serializes as a JSON string over the wire, exactly like REST's MoneyField
# (coerce_to_string=True) -- "Decimal never float for money" applies here
# too, not just in REST. NewType + StrawberryConfig.scalar_map is the
# non-deprecated way to register a custom scalar (wrapping `Decimal`
# directly via strawberry.scalar(cls=...) triggers a deprecation warning).
DecimalScalar = NewType("DecimalScalar", Decimal)

decimal_scalar_definition = strawberry.scalar(
    name="Decimal",
    serialize=lambda value: str(value),
    parse_value=lambda value: Decimal(str(value)),
)
