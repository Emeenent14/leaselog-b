"""
Admin configuration for transactions app.
"""
from django.contrib import admin
from .models import Transaction, TransactionCategory


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'schedule_e_line', 'is_system']
    list_filter = ['type', 'is_system']
    search_fields = ['name']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['description', 'type', 'category', 'amount', 'date', 'property', 'owner']
    list_filter = ['type', 'category', 'tax_year', 'is_imported']
    search_fields = ['description', 'vendor_name', 'owner__email']
    ordering = ['-date']
    date_hierarchy = 'date'
