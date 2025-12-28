"""
Banking URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StripeAccountViewSet, PaymentMethodViewSet, PaymentIntentView,
    StripeWebhookView, PlaidConnectionViewSet, PlaidAccountViewSet,
    PlaidTransactionViewSet
)

router = DefaultRouter()
router.register(r'stripe/accounts', StripeAccountViewSet, basename='stripe-account')
router.register(r'stripe/payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'plaid/connections', PlaidConnectionViewSet, basename='plaid-connection')
router.register(r'plaid/accounts', PlaidAccountViewSet, basename='plaid-account')
router.register(r'plaid/transactions', PlaidTransactionViewSet, basename='plaid-transaction')

urlpatterns = [
    path('banking/', include(router.urls)),
    path('payments/create-intent/', PaymentIntentView.as_view(), name='create-payment-intent'),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
