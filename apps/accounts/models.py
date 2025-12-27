"""
User models for LeaseLog API.
"""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from core.models import BaseModel


class UserManager(BaseUserManager):
    """Custom user manager."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Remove username field
    email = models.EmailField(unique=True)

    # Profile
    phone = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)

    # Business Info
    company_name = models.CharField(max_length=255, blank=True)
    business_address = models.TextField(blank=True)

    # Subscription
    SUBSCRIPTION_TIERS = [
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('pro', 'Pro'),
        ('business', 'Business'),
    ]
    SUBSCRIPTION_STATUS = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('trialing', 'Trialing'),
    ]

    subscription_tier = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_TIERS,
        default='free'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS,
        default='active'
    )

    # Verification
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None

    @property
    def property_limit(self):
        """Get property limit based on subscription tier."""
        limits = {
            'free': 2,
            'starter': 5,
            'pro': 15,
            'business': float('inf'),
        }
        return limits.get(self.subscription_tier, 2)


class UserSettings(BaseModel):
    """User preferences and settings."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings'
    )

    # Notification Preferences
    email_rent_reminders = models.BooleanField(default=True)
    email_payment_received = models.BooleanField(default=True)
    email_lease_expiring = models.BooleanField(default=True)

    # Business Defaults
    default_rent_due_day = models.IntegerField(default=1)
    default_late_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00
    )
    default_late_fee_grace_days = models.IntegerField(default=5)
    default_lease_term_months = models.IntegerField(default=12)

    # Display Preferences
    timezone = models.CharField(max_length=50, default='America/New_York')
    date_format = models.CharField(max_length=20, default='MM/DD/YYYY')
    currency = models.CharField(max_length=3, default='USD')

    class Meta:
        db_table = 'user_settings'


class EmailVerificationToken(BaseModel):
    """Token for email verification."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'email_verification_tokens'


class PasswordResetToken(BaseModel):
    """Token for password reset."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'password_reset_tokens'
