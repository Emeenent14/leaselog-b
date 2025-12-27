"""
Property models for LeaseLog API.
"""
from django.db import models
from core.models import OwnedModel, BaseModel


class Property(OwnedModel):
    """Property model."""

    PROPERTY_TYPES = [
        ('single_family', 'Single Family'),
        ('multi_family', 'Multi Family'),
        ('condo', 'Condo'),
        ('apartment', 'Apartment'),
        ('duplex', 'Duplex'),
        ('triplex', 'Triplex'),
        ('fourplex', 'Fourplex'),
        ('commercial', 'Commercial'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('vacant', 'Vacant'),
        ('maintenance', 'Under Maintenance'),
        ('listed', 'Listed'),
        ('sold', 'Sold'),
        ('inactive', 'Inactive'),
    ]

    # Address
    street_address = models.CharField(max_length=255)
    unit_number = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)

    # Property Details
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    is_multi_unit = models.BooleanField(default=False)
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    square_feet = models.PositiveIntegerField(null=True, blank=True)
    lot_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    year_built = models.PositiveIntegerField(null=True, blank=True)

    # Financial
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Mortgage
    has_mortgage = models.BooleanField(default=False)
    mortgage_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mortgage_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mortgage_lender = models.CharField(max_length=100, blank=True)

    # Insurance
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_policy_number = models.CharField(max_length=50, blank=True)
    insurance_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    insurance_renewal_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Other
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'properties'
        verbose_name_plural = 'properties'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['city', 'state']),
        ]

    def __str__(self):
        if self.unit_number:
            return f"{self.street_address} #{self.unit_number}, {self.city}"
        return f"{self.street_address}, {self.city}"

    @property
    def full_address(self):
        parts = [self.street_address]
        if self.unit_number:
            parts.append(f"#{self.unit_number}")
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        return ", ".join(parts)

    @property
    def occupancy_status(self):
        """Return occupancy status based on units or direct leases."""
        if self.is_multi_unit:
            units = self.units.filter(is_deleted=False)
            if not units.exists():
                return 'vacant'
            occupied = units.filter(status='occupied').count()
            total = units.count()
            if occupied == 0:
                return 'vacant'
            if occupied == total:
                return 'occupied'
            return 'partial'
        else:
            # Check if there's an active lease
            from apps.leases.models import Lease
            active_lease = Lease.objects.filter(
                property=self,
                unit__isnull=True,
                status='active',
                is_deleted=False
            ).exists()
            return 'occupied' if active_lease else 'vacant'


class Unit(BaseModel):
    """Unit model for multi-unit properties."""

    STATUS_CHOICES = [
        ('occupied', 'Occupied'),
        ('vacant', 'Vacant'),
        ('maintenance', 'Under Maintenance'),
        ('listed', 'Listed'),
    ]

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='units'
    )

    unit_number = models.CharField(max_length=20)
    floor = models.PositiveIntegerField(null=True, blank=True)
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=1)
    square_feet = models.PositiveIntegerField(null=True, blank=True)
    market_rent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='vacant')
    features = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'units'
        ordering = ['unit_number']
        unique_together = ['property', 'unit_number']

    def __str__(self):
        return f"{self.property.street_address} - Unit {self.unit_number}"


class PropertyPhoto(BaseModel):
    """Property photos."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='photos'
    )
    url = models.URLField()
    caption = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'property_photos'
        ordering = ['sort_order', 'created_at']
