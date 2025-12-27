"""
Tenant models for LeaseLog API.
"""
from django.db import models
from core.models import OwnedModel


class Tenant(OwnedModel):
    """Tenant model."""

    STATUS_CHOICES = [
        ('applicant', 'Applicant'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('past', 'Past Tenant'),
        ('rejected', 'Rejected'),
    ]

    # Personal Info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    phone_secondary = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Employment
    employer = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    # Previous Address
    previous_address = models.TextField(blank=True)
    previous_landlord_name = models.CharField(max_length=200, blank=True)
    previous_landlord_phone = models.CharField(max_length=20, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applicant')

    # Portal Access
    portal_token = models.CharField(max_length=100, blank=True, unique=True, null=True)
    portal_token_expires = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
