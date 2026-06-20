import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.entities.managers import EntityQuerySet


class EntityType(models.TextChoices):
    HOUSEHOLD = "HOUSEHOLD", _("Household")
    BUSINESS = "BUSINESS", _("Business")
    PROPERTY = "PROPERTY", _("Property")
    SUPERANNUATION = "SUPERANNUATION", _("Superannuation")
    OTHER = "OTHER", _("Other")


class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=EntityType.choices, default=EntityType.OTHER)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="EntityMembership",
        related_name="entities",
    )

    objects = EntityQuerySet.as_manager()

    class Meta:
        verbose_name = _("entity")
        verbose_name_plural = _("entities")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class EntityRole(models.TextChoices):
    OWNER = "OWNER", _("Owner")
    EDITOR = "EDITOR", _("Editor")
    VIEWER = "VIEWER", _("Viewer")


class EntityMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entity_memberships",
    )
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=16, choices=EntityRole.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("entity membership")
        verbose_name_plural = _("entity memberships")
        constraints = [
            models.UniqueConstraint(fields=["user", "entity"], name="unique_user_entity_membership")
        ]
        indexes = [
            models.Index(fields=["entity", "role"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.entity} ({self.role})"
