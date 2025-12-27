"""
Lease models for LeaseLog API.
"""
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from core.models import OwnedModel, BaseModel


class Lease(OwnedModel):
    """Lease model."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Signature'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('renewed', 'Renewed'),
    ]

    LEASE_TYPE_CHOICES = [
        ('fixed', 'Fixed Term'),
        ('month_to_month', 'Month to Month'),
    ]

    LATE_FEE_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount'),
        ('percent', 'Percentage'),
        ('daily', 'Daily Amount'),
    ]

    # Relationships
    rental_property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        related_name='leases'
    )
    unit = models.ForeignKey(
        'properties.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leases'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='leases'
    )

    # Lease Term
    lease_type = models.CharField(max_length=20, choices=LEASE_TYPE_CHOICES, default='fixed')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Rent
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    rent_due_day = models.PositiveIntegerField(default=1)  # Day of month

    # Security Deposit
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    security_deposit_paid = models.BooleanField(default=False)
    security_deposit_paid_date = models.DateField(null=True, blank=True)

    # Late Fees
    late_fee_type = models.CharField(max_length=20, choices=LATE_FEE_TYPE_CHOICES, default='fixed')
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=50)
    late_fee_grace_days = models.PositiveIntegerField(default=5)

    # Auto-renewal
    auto_renew = models.BooleanField(default=False)
    renewal_term_months = models.PositiveIntegerField(default=12)

    # Termination
    terminated_date = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'leases'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['rental_property', 'status']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['end_date']),
        ]

    def __str__(self):
        return f"Lease: {self.tenant} at {self.rental_property}"

    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def days_until_expiry(self):
        if self.end_date:
            delta = self.end_date - timezone.now().date()
            return delta.days
        return None

    def generate_rent_schedule(self):
        """Generate rent payment schedule for the lease term."""
        from apps.payments.models import RentPayment

        if self.status not in ['active', 'pending']:
            return

        # Delete existing unpaid payments
        RentPayment.objects.filter(
            lease=self,
            status='pending'
        ).delete()

        current_date = self.start_date
        end_date = self.end_date

        while current_date <= end_date:
            # Calculate due date for this month
            due_day = min(self.rent_due_day, 28)  # Handle months with fewer days
            try:
                due_date = current_date.replace(day=due_day)
            except ValueError:
                # Month doesn't have this day, use last day
                due_date = current_date.replace(day=28)

            if due_date >= self.start_date and due_date <= end_date:
                RentPayment.objects.get_or_create(
                    lease=self,
                    due_date=due_date,
                    defaults={
                        'amount_due': self.rent_amount,
                        'status': 'pending'
                    }
                )

            # Move to next month
            current_date = current_date + relativedelta(months=1)


class LeaseAdditionalTenant(BaseModel):
    """Additional tenants on a lease."""

    lease = models.ForeignKey(
        Lease,
        on_delete=models.CASCADE,
        related_name='additional_tenants'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='additional_leases'
    )
    is_responsible_for_rent = models.BooleanField(default=False)

    class Meta:
        db_table = 'lease_additional_tenants'
        unique_together = ['lease', 'tenant']
