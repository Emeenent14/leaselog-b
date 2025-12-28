"""
Tenant portal admin configuration.
"""
from django.contrib import admin
from .models import TenantPortalAccess, TenantPortalSession


@admin.register(TenantPortalAccess)
class TenantPortalAccessAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'is_active', 'token_expires_at', 'last_accessed_at', 'created_at']
    list_filter = ['is_active', 'can_make_payments', 'can_submit_maintenance']
    search_fields = ['tenant__first_name', 'tenant__last_name', 'tenant__email']
    readonly_fields = ['access_token', 'last_accessed_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Tenant', {
            'fields': ('tenant',)
        }),
        ('Access', {
            'fields': ('access_token', 'token_expires_at', 'is_active', 'last_accessed_at')
        }),
        ('Permissions', {
            'fields': ('can_view_lease', 'can_view_payments', 'can_make_payments', 'can_submit_maintenance', 'can_view_documents')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TenantPortalSession)
class TenantPortalSessionAdmin(admin.ModelAdmin):
    list_display = ['portal_access', 'ip_address', 'expires_at', 'created_at']
    list_filter = ['expires_at']
    search_fields = ['portal_access__tenant__first_name', 'portal_access__tenant__last_name']
    readonly_fields = ['session_token', 'ip_address', 'user_agent', 'created_at', 'updated_at']
