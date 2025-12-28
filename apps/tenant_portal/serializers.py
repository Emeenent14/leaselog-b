"""
Tenant portal serializers.
"""
from rest_framework import serializers
from .models import TenantPortalAccess, TenantPortalSession


class TenantPortalAccessSerializer(serializers.ModelSerializer):
    """Serializer for tenant portal access."""

    tenant_name = serializers.CharField(source='tenant.full_name', read_only=True)
    tenant_email = serializers.CharField(source='tenant.email', read_only=True)
    portal_url = serializers.SerializerMethodField()

    class Meta:
        model = TenantPortalAccess
        fields = [
            'id', 'tenant', 'tenant_name', 'tenant_email',
            'access_token', 'token_expires_at', 'is_active',
            'can_view_lease', 'can_view_payments', 'can_make_payments',
            'can_submit_maintenance', 'can_view_documents',
            'last_accessed_at', 'portal_url', 'created_at'
        ]
        read_only_fields = ['id', 'tenant', 'access_token', 'token_expires_at',
                           'last_accessed_at', 'created_at']

    def get_portal_url(self, obj):
        from django.conf import settings
        return f"{settings.FRONTEND_URL}/tenant-portal/{obj.access_token}"


class TenantPortalLoginSerializer(serializers.Serializer):
    """Serializer for tenant portal login."""

    token = serializers.CharField()


class TenantPortalSessionSerializer(serializers.Serializer):
    """Serializer for tenant portal session response."""

    session_token = serializers.CharField()
    expires_at = serializers.DateTimeField()
    tenant = serializers.SerializerMethodField()

    def get_tenant(self, obj):
        tenant = obj.portal_access.tenant
        return {
            'id': str(tenant.id),
            'first_name': tenant.first_name,
            'last_name': tenant.last_name,
            'email': tenant.email,
        }


class TenantProfileSerializer(serializers.Serializer):
    """Serializer for tenant profile in portal."""

    id = serializers.UUIDField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()


class TenantLeaseSerializer(serializers.Serializer):
    """Serializer for tenant's lease in portal."""

    id = serializers.UUIDField()
    property_name = serializers.CharField()
    property_address = serializers.CharField()
    unit_name = serializers.CharField(allow_null=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    rent_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()


class TenantPaymentSerializer(serializers.Serializer):
    """Serializer for tenant's payments in portal."""

    id = serializers.UUIDField()
    due_date = serializers.DateField()
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    balance_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    late_fee_applied = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    paid_date = serializers.DateField(allow_null=True)


class TenantMakePaymentSerializer(serializers.Serializer):
    """Serializer for making a payment from portal."""

    rent_payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method_id = serializers.CharField(required=False)
    save_payment_method = serializers.BooleanField(default=False)


class TenantMaintenanceRequestSerializer(serializers.Serializer):
    """Serializer for tenant maintenance requests."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    priority = serializers.CharField(default='medium')
    status = serializers.CharField(read_only=True)
    permission_to_enter = serializers.BooleanField(default=False)
    preferred_times = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)


class TenantMaintenanceCommentSerializer(serializers.Serializer):
    """Serializer for tenant adding comments."""

    content = serializers.CharField()
