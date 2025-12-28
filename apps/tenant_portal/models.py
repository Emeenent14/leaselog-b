"""
Tenant portal models for tenant self-service.
"""
import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta
from core.models import BaseModel


class TenantPortalAccess(BaseModel):
    """Tenant portal access token and settings."""

    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='portal_access'
    )

    # Access token (used for passwordless login)
    access_token = models.CharField(max_length=100, unique=True)
    token_expires_at = models.DateTimeField()

    # Portal status
    is_active = models.BooleanField(default=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    # Permissions
    can_view_lease = models.BooleanField(default=True)
    can_view_payments = models.BooleanField(default=True)
    can_make_payments = models.BooleanField(default=True)
    can_submit_maintenance = models.BooleanField(default=True)
    can_view_documents = models.BooleanField(default=True)

    class Meta:
        db_table = 'tenant_portal_access'

    def __str__(self):
        return f"Portal access for {self.tenant.full_name}"

    @classmethod
    def create_for_tenant(cls, tenant, expires_days=365):
        """Create or refresh portal access for a tenant."""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=expires_days)

        access, created = cls.objects.update_or_create(
            tenant=tenant,
            defaults={
                'access_token': token,
                'token_expires_at': expires_at,
                'is_active': True,
            }
        )
        return access

    def refresh_token(self, expires_days=365):
        """Refresh the access token."""
        self.access_token = secrets.token_urlsafe(32)
        self.token_expires_at = timezone.now() + timedelta(days=expires_days)
        self.save()

    @property
    def is_valid(self):
        """Check if portal access is valid."""
        return self.is_active and self.token_expires_at > timezone.now()


class TenantPortalSession(BaseModel):
    """Track tenant portal sessions."""

    portal_access = models.ForeignKey(
        TenantPortalAccess,
        on_delete=models.CASCADE,
        related_name='sessions'
    )

    session_token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()

    # Session metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = 'tenant_portal_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Session for {self.portal_access.tenant.full_name}"

    @classmethod
    def create_session(cls, portal_access, ip_address=None, user_agent=''):
        """Create a new session."""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)

        session = cls.objects.create(
            portal_access=portal_access,
            session_token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Update last accessed
        portal_access.last_accessed_at = timezone.now()
        portal_access.save()

        return session

    @property
    def is_valid(self):
        """Check if session is valid."""
        return self.expires_at > timezone.now()
