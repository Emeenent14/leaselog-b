"""
URL configuration for LeaseLog API.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.views import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include([
        path('', include('apps.accounts.urls')),
        path('', include('apps.properties.urls')),
        path('', include('apps.tenants.urls')),
        path('', include('apps.leases.urls')),
        path('', include('apps.transactions.urls')),
        path('', include('apps.payments.urls')),
        path('', include('apps.reports.urls')),

        # Phase 2
        path('', include('apps.banking.urls')),
        path('', include('apps.documents.urls')),
        path('', include('apps.maintenance.urls')),
        path('', include('apps.tenant_portal.urls')),

        # Health check
        path('health/', HealthCheckView.as_view(), name='health_check'),
    ])),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
