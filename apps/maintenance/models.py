"""
Maintenance models for maintenance request tracking.
"""
from django.db import models
from django.conf import settings
from core.models import BaseModel


class MaintenanceRequest(BaseModel):
    """Maintenance request model."""

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('emergency', 'Emergency'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending_parts', 'Pending Parts'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    CATEGORY_CHOICES = [
        ('plumbing', 'Plumbing'),
        ('electrical', 'Electrical'),
        ('hvac', 'HVAC'),
        ('appliance', 'Appliance'),
        ('structural', 'Structural'),
        ('pest', 'Pest Control'),
        ('landscaping', 'Landscaping'),
        ('cleaning', 'Cleaning'),
        ('safety', 'Safety'),
        ('other', 'Other'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='maintenance_requests'
    )

    # Location
    rental_property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        related_name='maintenance_requests'
    )
    unit = models.ForeignKey(
        'properties.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_requests'
    )

    # Requester
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_requests'
    )
    submitted_by_tenant = models.BooleanField(default=False)

    # Request details
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    # Permission
    permission_to_enter = models.BooleanField(default=False)
    preferred_times = models.TextField(blank=True)  # When tenant is available

    # Scheduling
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)

    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    # Costs
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Link to expense transaction
    expense_transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_request'
    )

    # Vendor/contractor
    vendor_name = models.CharField(max_length=200, blank=True)
    vendor_phone = models.CharField(max_length=20, blank=True)
    vendor_email = models.EmailField(blank=True)

    class Meta:
        db_table = 'maintenance_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['rental_property', 'status']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.rental_property.name}"

    @property
    def is_open(self):
        return self.status in ['open', 'in_progress', 'pending_parts', 'scheduled']


class MaintenanceComment(BaseModel):
    """Comments on maintenance requests."""

    request = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    # Author - either landlord or tenant
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_comments'
    )
    author_tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_comments'
    )

    content = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal notes not visible to tenant

    class Meta:
        db_table = 'maintenance_comments'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on {self.request.title}"

    @property
    def author_name(self):
        if self.author_user:
            return self.author_user.full_name
        if self.author_tenant:
            return self.author_tenant.full_name
        return "Unknown"


class MaintenancePhoto(BaseModel):
    """Photos attached to maintenance requests."""

    request = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name='photos'
    )

    # Storage
    file_key = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    content_type = models.CharField(max_length=100)

    # Metadata
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by_tenant = models.BooleanField(default=False)

    class Meta:
        db_table = 'maintenance_photos'
        ordering = ['created_at']

    def __str__(self):
        return f"Photo for {self.request.title}"
