"""
Tenant portal URL configuration.
"""
from django.urls import path
from .views import (
    TenantPortalLoginView, TenantPortalProfileView, TenantPortalLeaseView,
    TenantPortalPaymentsView, TenantPortalMakePaymentView,
    TenantPortalMaintenanceView, TenantPortalMaintenanceDetailView,
    TenantPortalAccessView
)

urlpatterns = [
    # Tenant-facing endpoints
    path('tenant-portal/auth/', TenantPortalLoginView.as_view(), name='tenant-portal-login'),
    path('tenant-portal/profile/', TenantPortalProfileView.as_view(), name='tenant-portal-profile'),
    path('tenant-portal/lease/', TenantPortalLeaseView.as_view(), name='tenant-portal-lease'),
    path('tenant-portal/payments/', TenantPortalPaymentsView.as_view(), name='tenant-portal-payments'),
    path('tenant-portal/payments/create/', TenantPortalMakePaymentView.as_view(), name='tenant-portal-make-payment'),
    path('tenant-portal/maintenance/', TenantPortalMaintenanceView.as_view(), name='tenant-portal-maintenance'),
    path('tenant-portal/maintenance/<uuid:pk>/', TenantPortalMaintenanceDetailView.as_view(), name='tenant-portal-maintenance-detail'),

    # Landlord endpoints for managing portal access
    path('tenants/<uuid:tenant_id>/portal-access/', TenantPortalAccessView.as_view(), name='tenant-portal-access'),
]
