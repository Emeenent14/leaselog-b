"""
Maintenance URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MaintenanceRequestViewSet

router = DefaultRouter()
router.register(r'maintenance', MaintenanceRequestViewSet, basename='maintenance')

urlpatterns = [
    path('', include(router.urls)),
]
