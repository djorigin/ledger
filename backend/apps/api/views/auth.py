from rest_framework.generics import RetrieveAPIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.api.serializers.auth import MeSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    """Stock simplejwt behavior; USERNAME_FIELD="email" already makes this
    accept {"email": ..., "password": ...}. Subclassed (not used directly)
    so future login-specific behavior (audit logging, throttling) has a
    home without an import-path change for apps.api.urls."""


class MeView(RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user
