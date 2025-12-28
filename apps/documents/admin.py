"""
Documents admin configuration.
"""
from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'owner', 'rental_property', 'tenant', 'lease', 'is_uploaded', 'created_at']
    list_filter = ['type', 'is_uploaded']
    search_fields = ['name', 'description', 'file_name']
    readonly_fields = ['file_key', 'file_size', 'content_type', 'is_uploaded', 'uploaded_at', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Document Info', {
            'fields': ('name', 'description', 'type', 'tags', 'expiry_date')
        }),
        ('File Info', {
            'fields': ('file_key', 'file_name', 'file_size', 'content_type', 'is_uploaded', 'uploaded_at')
        }),
        ('Relationships', {
            'fields': ('owner', 'rental_property', 'unit', 'tenant', 'lease', 'transaction', 'maintenance_request')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
