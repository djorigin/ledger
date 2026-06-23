"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.api.graphql.schema import schema
from apps.api.graphql.views import LedgerGraphQLView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.api.urls')),
    # Not nested under /api/v1/ -- a GraphQL endpoint isn't versioned the
    # way REST paths are; the schema itself is the compatibility surface.
    path('graphql/', LedgerGraphQLView.as_view(schema=schema), name='graphql'),
]

# Dev-only: serves MEDIA_ROOT directly (Inventory photo uploads). In prod
# this is a no-op (DEBUG=False) -- nginx serves /media/ from a shared
# volume instead, see nginx/nginx.conf.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
