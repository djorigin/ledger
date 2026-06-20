from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.currencies.services import backfill_exchange_rates


class Command(BaseCommand):
    help = "Backfill historical ExchangeRate rows for a date range (inclusive)."

    def add_arguments(self, parser):
        parser.add_argument("start_date", type=date.fromisoformat)
        parser.add_argument("end_date", type=date.fromisoformat)

    def handle(self, *args, **options):
        start_date = options["start_date"]
        end_date = options["end_date"]
        if start_date > end_date:
            raise CommandError("start_date must be on or before end_date.")
        rows = backfill_exchange_rates(start_date=start_date, end_date=end_date)
        self.stdout.write(
            self.style.SUCCESS(f"Backfilled/confirmed {len(rows)} exchange rate rows.")
        )
