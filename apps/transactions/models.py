"""
Transaction models for LeaseLog API.
"""
from django.db import models
from core.models import OwnedModel, BaseModel


class TransactionCategory(BaseModel):
    """Transaction category model."""

    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    schedule_e_line = models.CharField(max_length=50, blank=True)
    is_system = models.BooleanField(default=False)
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_categories'
    )

    class Meta:
        db_table = 'transaction_categories'
        verbose_name_plural = 'transaction categories'
        ordering = ['type', 'name']

    def __str__(self):
        return f"{self.name} ({self.type})"


class Transaction(OwnedModel):
    """Transaction model for income and expenses."""

    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('online', 'Online Payment'),
        ('other', 'Other'),
    ]

    # Type and Category
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.ForeignKey(
        TransactionCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions'
    )

    # Relationships
    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    unit = models.ForeignKey(
        'properties.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    lease = models.ForeignKey(
        'leases.Lease',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    # Transaction Details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=500)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True
    )
    reference_number = models.CharField(max_length=100, blank=True)
    vendor_name = models.CharField(max_length=255, blank=True)

    # Receipt
    receipt_url = models.URLField(blank=True)

    # Tax
    is_tax_deductible = models.BooleanField(default=True)
    tax_year = models.PositiveIntegerField(null=True, blank=True)

    # Import tracking
    is_imported = models.BooleanField(default=False)
    import_source = models.CharField(max_length=50, blank=True)
    external_id = models.CharField(max_length=100, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['owner', 'type', 'date']),
            models.Index(fields=['property', 'date']),
            models.Index(fields=['tax_year']),
        ]

    def __str__(self):
        return f"{self.type}: {self.amount} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        # Auto-set tax year from date
        if self.date and not self.tax_year:
            self.tax_year = self.date.year
        super().save(*args, **kwargs)
