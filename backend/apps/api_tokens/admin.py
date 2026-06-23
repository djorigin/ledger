import secrets

from django.contrib import admin, messages

from apps.api_tokens.models import APIToken


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ["name", "token_prefix", "scope", "created_by", "last_used_at", "created_at"]
    list_filter = ["scope"]
    search_fields = ["name"]
    autocomplete_fields = ["created_by"]

    def get_fields(self, request, obj=None):
        if obj is None:
            return ["name", "scope"]
        return ["name", "token_prefix", "scope", "created_by", "last_used_at", "created_at"]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ["token_prefix", "created_by", "last_used_at", "created_at"]

    def save_model(self, request, obj, form, change):
        if not change:
            # Generated here, not via APIToken.generate(), because admin's
            # add flow needs to mutate this exact in-flight `obj` (Django
            # persists the same object reference it was given) rather than
            # create a second row.
            plaintext = secrets.token_urlsafe(32)
            obj.token_hash = APIToken.hash_token(plaintext)
            obj.token_prefix = plaintext[:8]
            obj.created_by = request.user
            self._plaintext_token = plaintext
        obj.save()

    def response_add(self, request, obj, post_url_continue=None):
        response = super().response_add(request, obj, post_url_continue)
        plaintext = getattr(self, "_plaintext_token", None)
        if plaintext:
            messages.warning(
                request,
                f"API token for '{obj.name}' (shown once -- copy it now, it cannot be retrieved "
                f"again): {plaintext}",
            )
            del self._plaintext_token
        return response
