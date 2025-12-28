"""
Banking serializers for Stripe and Plaid.
"""
from rest_framework import serializers
from .models import (
    StripeAccount, PaymentMethod, StripePayment,
    PlaidConnection, PlaidAccount, PlaidTransaction
)


class StripeAccountSerializer(serializers.ModelSerializer):
    """Serializer for Stripe Connect account."""

    class Meta:
        model = StripeAccount
        fields = [
            'id', 'stripe_account_id', 'charges_enabled', 'payouts_enabled',
            'details_submitted', 'account_type', 'onboarding_completed_at',
            'created_at'
        ]
        read_only_fields = fields


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for saved payment methods."""

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'type', 'last_four', 'brand', 'exp_month', 'exp_year',
            'bank_name', 'account_type', 'is_default', 'display_name',
            'created_at'
        ]
        read_only_fields = fields

    def get_display_name(self, obj):
        if obj.type == 'card':
            return f"{obj.brand.title()} ending in {obj.last_four}"
        return f"{obj.bank_name} ending in {obj.last_four}"


class StripePaymentSerializer(serializers.ModelSerializer):
    """Serializer for Stripe payments."""

    payment_method_display = PaymentMethodSerializer(source='payment_method', read_only=True)

    class Meta:
        model = StripePayment
        fields = [
            'id', 'rent_payment', 'stripe_payment_intent_id', 'amount',
            'currency', 'status', 'stripe_fee', 'failure_code',
            'failure_message', 'payment_method_display', 'created_at'
        ]
        read_only_fields = fields


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating a payment intent."""

    rent_payment_id = serializers.UUIDField()
    payment_method_id = serializers.CharField(required=False)
    save_payment_method = serializers.BooleanField(default=False)


class PlaidConnectionSerializer(serializers.ModelSerializer):
    """Serializer for Plaid connections."""

    accounts_count = serializers.SerializerMethodField()

    class Meta:
        model = PlaidConnection
        fields = [
            'id', 'institution_id', 'institution_name', 'institution_logo',
            'status', 'error_code', 'error_message', 'last_synced_at',
            'accounts_count', 'created_at'
        ]
        read_only_fields = fields

    def get_accounts_count(self, obj):
        return obj.accounts.count()


class PlaidAccountSerializer(serializers.ModelSerializer):
    """Serializer for Plaid accounts."""

    institution_name = serializers.CharField(source='connection.institution_name', read_only=True)

    class Meta:
        model = PlaidAccount
        fields = [
            'id', 'name', 'official_name', 'mask', 'type', 'subtype',
            'current_balance', 'available_balance', 'sync_transactions',
            'institution_name'
        ]
        read_only_fields = ['id', 'name', 'official_name', 'mask', 'type',
                           'subtype', 'current_balance', 'available_balance',
                           'institution_name']


class PlaidTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Plaid transactions."""

    account_name = serializers.CharField(source='account.name', read_only=True)
    account_mask = serializers.CharField(source='account.mask', read_only=True)

    class Meta:
        model = PlaidTransaction
        fields = [
            'id', 'account', 'account_name', 'account_mask', 'date', 'name',
            'merchant_name', 'amount', 'plaid_category', 'status', 'pending',
            'matched_transaction', 'created_at'
        ]
        read_only_fields = ['id', 'account', 'account_name', 'account_mask',
                           'date', 'name', 'merchant_name', 'amount',
                           'plaid_category', 'pending', 'created_at']


class CategorizeTransactionSerializer(serializers.Serializer):
    """Serializer for categorizing a Plaid transaction."""

    category_id = serializers.UUIDField()
    property_id = serializers.UUIDField(required=False)
    description = serializers.CharField(required=False)


class PlaidLinkTokenSerializer(serializers.Serializer):
    """Serializer for Plaid Link token response."""

    link_token = serializers.CharField()
    expiration = serializers.DateTimeField()


class PlaidExchangeTokenSerializer(serializers.Serializer):
    """Serializer for exchanging Plaid public token."""

    public_token = serializers.CharField()
