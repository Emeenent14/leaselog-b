"""
Banking models for Stripe and Plaid integrations.
"""
from django.db import models
from django.conf import settings
from core.models import BaseModel


class StripeAccount(BaseModel):
    """Stripe Connect account for landlords."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stripe_account'
    )
    stripe_account_id = models.CharField(max_length=100, unique=True)

    # Account status
    charges_enabled = models.BooleanField(default=False)
    payouts_enabled = models.BooleanField(default=False)
    details_submitted = models.BooleanField(default=False)

    # Account type
    account_type = models.CharField(max_length=20, default='express')  # express, standard, custom

    # Metadata
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'stripe_accounts'

    def __str__(self):
        return f"Stripe Account for {self.user.email}"


class PaymentMethod(BaseModel):
    """Saved payment methods for tenants."""

    TYPE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('bank_account', 'Bank Account (ACH)'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    stripe_payment_method_id = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    # Card details (masked)
    last_four = models.CharField(max_length=4)
    brand = models.CharField(max_length=20, blank=True)  # visa, mastercard, etc.
    exp_month = models.IntegerField(null=True, blank=True)
    exp_year = models.IntegerField(null=True, blank=True)

    # Bank account details (masked)
    bank_name = models.CharField(max_length=100, blank=True)
    account_type = models.CharField(max_length=20, blank=True)  # checking, savings

    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'payment_methods'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.type} ending in {self.last_four}"


class StripePayment(BaseModel):
    """Stripe payment records."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('canceled', 'Canceled'),
    ]

    rent_payment = models.ForeignKey(
        'payments.RentPayment',
        on_delete=models.CASCADE,
        related_name='stripe_payments'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Stripe IDs
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True)
    stripe_charge_id = models.CharField(max_length=100, blank=True)

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Fees
    stripe_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Metadata
    failure_code = models.CharField(max_length=100, blank=True)
    failure_message = models.TextField(blank=True)

    class Meta:
        db_table = 'stripe_payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} - {self.status}"


class PlaidConnection(BaseModel):
    """Plaid bank connection for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='plaid_connections'
    )

    # Plaid identifiers
    plaid_item_id = models.CharField(max_length=100, unique=True)
    plaid_access_token = models.CharField(max_length=200)  # Should be encrypted

    # Institution info
    institution_id = models.CharField(max_length=50)
    institution_name = models.CharField(max_length=200)
    institution_logo = models.URLField(blank=True)

    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('error', 'Error'),
        ('disconnected', 'Disconnected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)

    # Sync tracking
    last_synced_at = models.DateTimeField(null=True, blank=True)
    cursor = models.CharField(max_length=500, blank=True)  # For transaction sync

    class Meta:
        db_table = 'plaid_connections'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.institution_name} - {self.user.email}"


class PlaidAccount(BaseModel):
    """Individual bank account from a Plaid connection."""

    connection = models.ForeignKey(
        PlaidConnection,
        on_delete=models.CASCADE,
        related_name='accounts'
    )

    # Plaid identifiers
    plaid_account_id = models.CharField(max_length=100, unique=True)

    # Account info
    name = models.CharField(max_length=200)
    official_name = models.CharField(max_length=200, blank=True)
    mask = models.CharField(max_length=4)  # Last 4 digits

    TYPE_CHOICES = [
        ('depository', 'Depository'),
        ('credit', 'Credit'),
        ('loan', 'Loan'),
        ('investment', 'Investment'),
        ('other', 'Other'),
    ]
    SUBTYPE_CHOICES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit card', 'Credit Card'),
        ('money market', 'Money Market'),
        ('other', 'Other'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subtype = models.CharField(max_length=30)

    # Balances
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    # Sync settings
    sync_transactions = models.BooleanField(default=True)

    class Meta:
        db_table = 'plaid_accounts'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (*{self.mask})"


class PlaidTransaction(BaseModel):
    """Imported transaction from Plaid."""

    account = models.ForeignKey(
        PlaidAccount,
        on_delete=models.CASCADE,
        related_name='plaid_transactions'
    )

    # Plaid identifiers
    plaid_transaction_id = models.CharField(max_length=100, unique=True)

    # Transaction details
    date = models.DateField()
    name = models.CharField(max_length=500)
    merchant_name = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # Positive = debit, Negative = credit

    # Categorization
    plaid_category = models.JSONField(default=list)  # Plaid's category hierarchy
    plaid_category_id = models.CharField(max_length=50, blank=True)

    # Matching to LeaseLog transaction
    matched_transaction = models.OneToOneField(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plaid_source'
    )

    # Review status
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('categorized', 'Categorized'),
        ('ignored', 'Ignored'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Pending indicator
    pending = models.BooleanField(default=False)

    class Meta:
        db_table = 'plaid_transactions'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['account', 'status']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.date} - {self.name} - ${self.amount}"
