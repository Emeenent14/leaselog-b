"""
Banking admin configuration.
"""
from django.contrib import admin
from .models import (
    StripeAccount, PaymentMethod, StripePayment,
    PlaidConnection, PlaidAccount, PlaidTransaction
)


@admin.register(StripeAccount)
class StripeAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'stripe_account_id', 'charges_enabled', 'payouts_enabled', 'created_at']
    list_filter = ['charges_enabled', 'payouts_enabled', 'details_submitted']
    search_fields = ['user__email', 'stripe_account_id']
    readonly_fields = ['stripe_account_id', 'created_at', 'updated_at']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'type', 'last_four', 'brand', 'is_default', 'created_at']
    list_filter = ['type', 'is_default']
    search_fields = ['tenant__first_name', 'tenant__last_name', 'last_four']
    readonly_fields = ['stripe_payment_method_id', 'created_at', 'updated_at']


@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ['rent_payment', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['stripe_payment_intent_id', 'stripe_charge_id']
    readonly_fields = ['stripe_payment_intent_id', 'stripe_charge_id', 'created_at', 'updated_at']


@admin.register(PlaidConnection)
class PlaidConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'institution_name', 'status', 'last_synced_at', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email', 'institution_name']
    readonly_fields = ['plaid_item_id', 'created_at', 'updated_at']


@admin.register(PlaidAccount)
class PlaidAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'connection', 'type', 'subtype', 'mask', 'current_balance']
    list_filter = ['type', 'subtype', 'sync_transactions']
    search_fields = ['name', 'official_name']
    readonly_fields = ['plaid_account_id', 'created_at', 'updated_at']


@admin.register(PlaidTransaction)
class PlaidTransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'amount', 'account', 'status', 'pending']
    list_filter = ['status', 'pending', 'date']
    search_fields = ['name', 'merchant_name']
    readonly_fields = ['plaid_transaction_id', 'created_at', 'updated_at']
    date_hierarchy = 'date'
