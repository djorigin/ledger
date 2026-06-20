from celery import shared_task

from apps.currencies.services import fetch_latest_exchange_rates as _fetch_latest_exchange_rates


@shared_task(name="apps.currencies.tasks.fetch_latest_exchange_rates")
def fetch_latest_exchange_rates():
    _fetch_latest_exchange_rates()
