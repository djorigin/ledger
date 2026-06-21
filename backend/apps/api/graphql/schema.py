import strawberry
from strawberry.schema.config import StrawberryConfig

from apps.api.graphql.queries import Query
from apps.api.graphql.scalars import DecimalScalar, decimal_scalar_definition

schema = strawberry.Schema(
    query=Query,
    config=StrawberryConfig(scalar_map={DecimalScalar: decimal_scalar_definition}),
)
