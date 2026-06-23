from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from apps.assets.models import AssetClass
from apps.currencies.services import convert


@dataclass(frozen=True)
class AssetClassValue:
    asset: AssetClass
    value: Decimal
    as_of: date | None


@dataclass(frozen=True)
class AssetRegisterNetWorth:
    reporting_currency: str
    rows: list[AssetClassValue]
    total: Decimal


def compute_asset_register_net_worth(entities, *, reporting_currency) -> AssetRegisterNetWorth:
    """
    Asset-register-only net worth: each active asset's *latest* valuation
    (falling back to acquisition_cost/date if no valuation has been
    recorded yet), converted to reporting_currency at the rate on the
    valuation/acquisition date -- a historical estimate converts at the
    rate that applied then, same reasoning as compute_project_actuals.
    Assets with neither a valuation nor an acquisition_cost contribute
    nothing (not yet valued). `entities` must already be access-filtered
    by the caller, same convention as compute_net_worth.
    """
    rows = []
    for entity in entities:
        for asset in AssetClass.objects.filter(entity=entity, is_active=True):
            latest = asset.latest_valuation
            if latest is not None:
                value, as_of, currency = latest.current_value, latest.valuation_date, latest.currency
            elif asset.acquisition_cost is not None and asset.acquisition_date is not None:
                value, as_of, currency = asset.acquisition_cost, asset.acquisition_date, asset.currency
            else:
                continue

            converted = convert(
                amount=value, from_currency=currency, to_currency=reporting_currency, on_date=as_of
            )
            rows.append(AssetClassValue(asset=asset, value=converted, as_of=as_of))

    total = sum((r.value for r in rows), Decimal("0"))
    return AssetRegisterNetWorth(reporting_currency=reporting_currency, rows=rows, total=total)
