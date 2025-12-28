"""
Document models for file storage and management.
"""
from django.db import models
from django.conf import settings
from core.models import BaseModel


class Document(BaseModel):
    """Document storage model."""

    TYPE_CHOICES = [
        ('lease', 'Lease Agreement'),
        ('addendum', 'Lease Addendum'),
        ('application', 'Rental Application'),
        ('id', 'ID/Verification'),
        ('receipt', 'Receipt'),
        ('invoice', 'Invoice'),
        ('insurance', 'Insurance'),
        ('inspection', 'Inspection Report'),
        ('photo', 'Photo'),
        ('other', 'Other'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    # Document info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')

    # File storage
    file_key = models.CharField(max_length=500)  # S3/R2 key
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()  # bytes
    content_type = models.CharField(max_length=100)

    # Relationships (optional - document can be linked to multiple entities)
    rental_property = models.ForeignKey(
        'properties.Property',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    unit = models.ForeignKey(
        'properties.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    lease = models.ForeignKey(
        'leases.Lease',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    maintenance_request = models.ForeignKey(
        'maintenance.MaintenanceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )

    # Metadata
    tags = models.JSONField(default=list)
    expiry_date = models.DateField(null=True, blank=True)  # For insurance docs, etc.

    # Upload status
    is_uploaded = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'type']),
            models.Index(fields=['rental_property']),
            models.Index(fields=['lease']),
        ]

    def __str__(self):
        return f"{self.name} ({self.type})"

    @property
    def file_extension(self):
        """Get file extension from file name."""
        if '.' in self.file_name:
            return self.file_name.rsplit('.', 1)[1].lower()
        return ''

    @property
    def is_image(self):
        """Check if document is an image."""
        return self.content_type.startswith('image/')

    @property
    def is_pdf(self):
        """Check if document is a PDF."""
        return self.content_type == 'application/pdf'
