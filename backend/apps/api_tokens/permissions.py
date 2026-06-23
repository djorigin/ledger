from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.api_tokens.authentication import APITokenAuthentication


class DenyWriteForApiToken(BasePermission):
    """
    Added to REST_FRAMEWORK's DEFAULT_PERMISSION_CLASSES. Note this alone
    is *not* sufficient: most viewsets here override `get_permissions()`,
    which replaces the default permission list entirely rather than
    extending it, so this class never runs for those views. The actual
    universal enforcement is apps.api_tokens.middleware.DenyApiTokenWriteMiddleware
    (runs before any view code, regardless of per-view overrides); this
    class is defense-in-depth for the few views that don't override
    get_permissions() and so still consult the defaults.
    """

    def has_permission(self, request, view):
        if isinstance(request.successful_authenticator, APITokenAuthentication):
            return request.method in SAFE_METHODS
        return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
