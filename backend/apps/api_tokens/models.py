import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class APITokenScope(models.TextChoices):
    READ_ONLY = "READ_ONLY", _("Read only")


class APIToken(models.Model):
    """
    Long-lived, read-only token for Google Sheets (or similar) polling --
    separate from the JWT access/refresh flow the React frontend uses,
    since Apps Script can't do JWT's rotating-refresh-token dance. Only
    the SHA-256 hash is ever stored; the plaintext is shown exactly once,
    at creation, via AdminAPITokenAdmin's response_add override -- the
    standard personal-access-token pattern. Authenticates as
    `created_by` (see apps/api_tokens/authentication.py); read-only is
    enforced globally via DenyWriteForApiToken, not per-view.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="e.g. 'Google Sheets net worth sync'")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    token_prefix = models.CharField(
        max_length=8, editable=False, help_text="First 8 characters, for identifying a token in a list"
    )
    scope = models.CharField(max_length=16, choices=APITokenScope.choices, default=APITokenScope.READ_ONLY)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.token_prefix}...)"

    @staticmethod
    def hash_token(plaintext: str) -> str:
        return hashlib.sha256(plaintext.encode()).hexdigest()

    @classmethod
    def generate(cls, *, name, created_by, scope=APITokenScope.READ_ONLY):
        """Returns (instance, plaintext) -- the only time the plaintext is
        ever available; only its hash is persisted."""
        plaintext = secrets.token_urlsafe(32)
        instance = cls.objects.create(
            name=name,
            token_hash=cls.hash_token(plaintext),
            token_prefix=plaintext[:8],
            scope=scope,
            created_by=created_by,
        )
        return instance, plaintext
