"""
Payment models for LeaseLog API.
"""
from django.db import models
from core.models import BaseModel


class RentPayment(BaseModel):
    """Rent payment tracking model."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]

    lease = models.ForeignKey(
        'leases.Lease',
        on_delete=models.CASCADE,
        related_name='rent_payments'
    )

    # Payment details
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Late fee
    late_fee_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee_waived = models.BooleanField(default=False)
    late_fee_waived_reason = models.TextField(blank=True)

    # Payment date
    paid_date = models.DateField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'rent_payments'
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['lease', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]
        unique_together = ['lease', 'due_date']

    def __str__(self):
        return f"Rent for {self.lease.tenant} - {self.due_date}"

    @property
    def balance_due(self):
        return self.amount_due + self.late_fee_applied - self.amount_paid

    @property
    def is_late(self):
        from django.utils import timezone
        if self.status == 'paid':
            return False
        return self.due_date < timezone.now().date()

    def apply_late_fee(self):
        """Apply late fee based on lease settings."""
        if self.late_fee_applied > 0 or self.late_fee_waived:
            return

        lease = self.lease
        if lease.late_fee_type == 'fixed':
            self.late_fee_applied = lease.late_fee_amount
        elif lease.late_fee_type == 'percent':
            self.late_fee_applied = self.amount_due * (lease.late_fee_amount / 100)
        elif lease.late_fee_type == 'daily':
            from django.utils import timezone
            days_late = (timezone.now().date() - self.due_date).days - lease.late_fee_grace_days
            if days_late > 0:
                self.late_fee_applied = lease.late_fee_amount * days_late

        self.save()


class PaymentRecord(BaseModel):
    """Individual payment record (for partial payments)."""

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('online', 'Online Payment'),
        ('other', 'Other'),
    ]

    rent_payment = models.ForeignKey(
        RentPayment,
        on_delete=models.CASCADE,
        related_name='payment_records'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='other'
    )
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    # Link to transaction
    transaction = models.OneToOneField(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_record'
    )

    class Meta:
        db_table = 'payment_records'
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} on {self.payment_date}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update rent payment totals
        rent_payment = self.rent_payment
        total_paid = sum(
            record.amount for record in rent_payment.payment_records.all()
        )
        rent_payment.amount_paid = total_paid
        if total_paid >= (rent_payment.amount_due + rent_payment.late_fee_applied):
            rent_payment.status = 'paid'
            rent_payment.paid_date = self.payment_date
        elif total_paid > 0:
            rent_payment.status = 'partial'
        rent_payment.save()
