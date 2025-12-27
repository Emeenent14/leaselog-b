"""
Admin configuration for tenants app.
"""
from django.contrib import admin
from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'status', 'owner', 'created_at']
    list_filter = ['status']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'owner__email']
    ordering = ['last_name', 'first_name']
