import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.inventory.managers import InventoryItemQuerySet
from apps.ledger.constants import validate_currency_code


class InventoryCategory(models.TextChoices):
    ELECTRONICS = "ELECTRONICS", _("Electronics")
    APPLIANCES = "APPLIANCES", _("Appliances")
    FURNITURE = "FURNITURE", _("Furniture")
    TOOLS = "TOOLS", _("Tools")
    CLOTHING = "CLOTHING", _("Clothing")
    JEWELLERY = "JEWELLERY", _("Jewellery")
    COLLECTIBLES = "COLLECTIBLES", _("Collectibles")
    OTHER = "OTHER", _("Other")


class InventoryItem(models.Model):
    """
    Standalone -- for insurance purposes, a record of physical items with
    values. No GL linkage, same as AssetClass/AssetValuation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey("entities.Entity", on_delete=models.PROTECT, related_name="inventory_items")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=InventoryCategory.choices)
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=255, blank=True)
    model_number = models.CharField(max_length=255, blank=True)
    serial_number = models.CharField(max_length=255, blank=True)
    location = models.CharField(
        max_length=255, blank=True, help_text="e.g. Mount Gambier house -- living room"
    )
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    estimated_replacement_value = models.DecimalField(
        max_digits=19, decimal_places=4, null=True, blank=True
    )
    currency = models.CharField(max_length=3, validators=[validate_currency_code])
    insured = models.BooleanField(default=False)
    insurer = models.CharField(max_length=255, blank=True)
    policy_number = models.CharField(max_length=255, blank=True)
    photo = models.ImageField(upload_to="inventory/", null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = InventoryItemQuerySet.as_manager()

    class Meta:
        ordering = ["entity", "category", "name"]
        indexes = [models.Index(fields=["entity", "category"]), models.Index(fields=["entity", "insured"])]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
