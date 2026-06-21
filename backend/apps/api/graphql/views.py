from django.contrib.auth.models import AnonymousUser
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from strawberry.django.views import GraphQLView


@method_decorator(csrf_exempt, name="dispatch")
class LedgerGraphQLView(GraphQLView):
    """
    strawberry's Django view is a plain CBV -- Django's AuthenticationMiddleware
    only populates request.user from session auth, never a JWT bearer header,
    so it won't "just work" here. Running the exact same JWTAuthentication
    class REST uses keeps auth identical between the two APIs rather than
    reimplementing it. csrf_exempt because auth here is a Bearer token the
    client must attach manually, not an auto-attached cookie -- the same
    reasoning DRF's APIView already applies for token-authenticated requests.
    """

    def get_context(self, request, response):
        auth_result = JWTAuthentication().authenticate(request)
        request.user = auth_result[0] if auth_result else AnonymousUser()
        return super().get_context(request, response)
