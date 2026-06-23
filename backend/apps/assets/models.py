import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.assets.managers import AssetClassQuerySet
from apps.ledger.constants import validate_currency_code


class AssetCategory(models.TextChoices):
    PROPERTY = "PROPERTY", _("Property")
    VEHICLE = "VEHICLE", _("Vehicle")
    SUPERANNUATION = "SUPERANNUATION", _("Superannuation")
    INVESTMENT = "INVESTMENT", _("Investment")
    OTHER = "OTHER", _("Other")


class AssetClass(models.Model):
    """
    Tracks the current estimated value of a significant asset (house, car,
    superannuation balance) over time via snapshots -- no depreciation
    calculations, and deliberately no link into the GL/journal engine.
    Standalone tracking, same as Inventory.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey("entities.Entity", on_delete=models.PROTECT, related_name="asset_classes")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=AssetCategory.choices)
    description = models.TextField(blank=True)
    acquisition_date = models.DateField(null=True, blank=True)
    acquisition_cost = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    currency = models.CharField(max_length=3, validators=[validate_currency_code])
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AssetClassQuerySet.as_manager()

    class Meta:
        ordering = ["entity", "category", "name"]
        indexes = [models.Index(fields=["entity", "category"])]
        verbose_name_plural = "asset classes"

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    @property
    def latest_valuation(self):
        return self.valuations.order_by("-valuation_date", "-created_at").first()


class AssetValuation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(AssetClass, on_delete=models.PROTECT, related_name="valuations")
    valuation_date = models.DateField()
    current_value = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.CharField(max_length=3, validators=[validate_currency_code])
    source = models.CharField(
        max_length=255, blank=True, help_text="e.g. REA estimate, super fund statement, own estimate"
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valuation_date"]
        get_latest_by = "valuation_date"
        indexes = [models.Index(fields=["asset", "valuation_date"])]

    def __str__(self):
        return f"{self.asset.name}: {self.current_value} {self.currency} as of {self.valuation_date}"
