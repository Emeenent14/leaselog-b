"""
Admin configuration for leases app.
"""
from django.contrib import admin
from .models import Lease, LeaseAdditionalTenant


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ['rental_property', 'tenant', 'start_date', 'end_date', 'rent_amount', 'status', 'owner']
    list_filter = ['status', 'lease_type']
    search_fields = ['rental_property__street_address', 'tenant__first_name', 'tenant__last_name', 'owner__email']
    ordering = ['-start_date']
    date_hierarchy = 'start_date'
