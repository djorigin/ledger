from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.api_tokens.models import APIToken


class APITokenAuthentication(BaseAuthentication):
    """
    `Authorization: Token <token>` -- deliberately not `Bearer`, which
    JWTAuthentication owns. JWTAuthentication raises (rather than
    returning None) on a malformed Bearer credential, which would break
    DRF's authenticator fallthrough if both classes shared that prefix;
    using DRF's other conventional scheme keeps the two authenticators
    fully independent. Resolves to (token.created_by, token) -- every
    existing accessible_by(user)/HasEntityRole check then works
    unchanged, since they only ever look at request.user.
    """

    keyword = b"token"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword:
            return None
        if len(auth) != 2:
            raise AuthenticationFailed("Invalid Token header. No credentials provided.")

        plaintext = auth[1].decode()
        token = APIToken.objects.select_related("created_by").filter(
            token_hash=APIToken.hash_token(plaintext)
        ).first()
        if token is None:
            raise AuthenticationFailed("Invalid or revoked API token.")

        APIToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
        return (token.created_by, token)

    def authenticate_header(self, request):
        return "Token"
