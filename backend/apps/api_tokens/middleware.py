from django.http import JsonResponse

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def is_token_scheme(request) -> bool:
    return request.headers.get("Authorization", "").lower().startswith("token ")


class DenyApiTokenWriteMiddleware:
    """
    Most viewsets in this codebase override `get_permissions()` to return
    a custom list (e.g. `[HasEntityRole(EntityRole.EDITOR)()]`), which
    *replaces* DRF's DEFAULT_PERMISSION_CLASSES entirely for that view --
    apps.api_tokens.permissions.DenyWriteForApiToken (a default permission
    class) would silently never run for any of them. Middleware runs
    before any view code at all, so it's the one place that actually
    guarantees "API tokens are read-only" universally, with zero changes
    to any individual view -- the permission class stays too, as
    defense-in-depth for the few views that don't override get_permissions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_token_scheme(request) and request.method not in SAFE_METHODS:
            return JsonResponse({"detail": "API tokens are read-only."}, status=403)
        return self.get_response(request)
