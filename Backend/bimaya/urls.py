"""Root URL configuration for the Bimaya project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# API v1 — feature apps plug their routers/urls in here as they are built.
api_v1 = [
    path("", include("apps.core.urls")),
    # Phase 1 wiring (added as each app lands):
    # path("auth/", include("apps.accounts.urls")),
    # path("", include("apps.policies.urls")),
    # path("", include("apps.purchases.urls")),
    # path("", include("apps.payments.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Branding in the Django admin (used as the MVP admin panel).
admin.site.site_header = "Bimaya Administration"
admin.site.site_title = "Bimaya Admin"
admin.site.index_title = "Platform management"
