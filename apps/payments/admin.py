"""
Admin configuration for payments app.
"""
from django.contrib import admin
from .models import RentPayment, PaymentRecord


class PaymentRecordInline(admin.TabularInline):
    model = PaymentRecord
    extra = 0
    readonly_fields = ['transaction']


@admin.register(RentPayment)
class RentPaymentAdmin(admin.ModelAdmin):
    list_display = ['lease', 'due_date', 'amount_due', 'amount_paid', 'status']
    list_filter = ['status']
    search_fields = ['lease__tenant__first_name', 'lease__tenant__last_name', 'lease__property__street_address']
    ordering = ['-due_date']
    date_hierarchy = 'due_date'
    inlines = [PaymentRecordInline]
