"""
Maintenance admin configuration.
"""
from django.contrib import admin
from .models import MaintenanceRequest, MaintenanceComment, MaintenancePhoto


class MaintenanceCommentInline(admin.TabularInline):
    model = MaintenanceComment
    extra = 0
    readonly_fields = ['created_at']


class MaintenancePhotoInline(admin.TabularInline):
    model = MaintenancePhoto
    extra = 0
    readonly_fields = ['created_at']


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'rental_property', 'tenant', 'category', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority', 'category', 'submitted_by_tenant']
    search_fields = ['title', 'description', 'rental_property__name', 'tenant__first_name', 'tenant__last_name']
    readonly_fields = ['completed_at', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [MaintenanceCommentInline, MaintenancePhotoInline]

    fieldsets = (
        ('Request Info', {
            'fields': ('title', 'description', 'category', 'priority', 'status')
        }),
        ('Location', {
            'fields': ('owner', 'rental_property', 'unit', 'tenant', 'submitted_by_tenant')
        }),
        ('Scheduling', {
            'fields': ('permission_to_enter', 'preferred_times', 'scheduled_date', 'scheduled_time')
        }),
        ('Resolution', {
            'fields': ('completed_at', 'resolution_notes', 'estimated_cost', 'actual_cost', 'expense_transaction')
        }),
        ('Vendor', {
            'fields': ('vendor_name', 'vendor_phone', 'vendor_email'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaintenanceComment)
class MaintenanceCommentAdmin(admin.ModelAdmin):
    list_display = ['request', 'author_name', 'is_internal', 'created_at']
    list_filter = ['is_internal']
    search_fields = ['content', 'request__title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MaintenancePhoto)
class MaintenancePhotoAdmin(admin.ModelAdmin):
    list_display = ['request', 'file_name', 'uploaded_by_tenant', 'created_at']
    list_filter = ['uploaded_by_tenant']
    readonly_fields = ['created_at', 'updated_at']
