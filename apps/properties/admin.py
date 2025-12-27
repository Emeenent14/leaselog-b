"""
Admin configuration for properties app.
"""
from django.contrib import admin
from .models import Property, Unit, PropertyPhoto


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0
    fields = ['unit_number', 'bedrooms', 'bathrooms', 'square_feet', 'market_rent', 'status']


class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 0
    fields = ['url', 'caption', 'is_primary', 'sort_order']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['street_address', 'city', 'state', 'property_type', 'status', 'owner', 'created_at']
    list_filter = ['status', 'property_type', 'is_multi_unit', 'state']
    search_fields = ['street_address', 'city', 'owner__email']
    ordering = ['-created_at']
    inlines = [UnitInline, PropertyPhotoInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['unit_number', 'property', 'bedrooms', 'bathrooms', 'status']
    list_filter = ['status']
    search_fields = ['unit_number', 'property__street_address']
