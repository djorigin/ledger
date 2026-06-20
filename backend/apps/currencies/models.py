import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.ledger.constants import validate_currency_code


class ExchangeRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    from_currency = models.CharField(max_length=3, validators=[validate_currency_code])
    to_currency = models.CharField(max_length=3, validators=[validate_currency_code])
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    source = models.CharField(max_length=64, default="frankfurter.dev")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "from_currency", "to_currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "from_currency", "to_currency", "source"],
                name="unique_exchange_rate_per_date_pair_source",
            ),
        ]
        indexes = [
            models.Index(fields=["from_currency", "to_currency", "-date"]),
        ]

    def __str__(self):
        return f"{self.date} {self.from_currency}->{self.to_currency} {self.rate} ({self.source})"

    def clean(self):
        super().clean()
        if self.from_currency == self.to_currency:
            raise ValidationError(_("from_currency and to_currency must differ."))
