"""
Serializers for tenants app.
"""
from rest_framework import serializers
from .models import Tenant


class TenantListSerializer(serializers.ModelSerializer):
    """Serializer for tenant list view."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'status', 'created_at'
        ]


class TenantDetailSerializer(serializers.ModelSerializer):
    """Serializer for tenant detail view."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'phone_secondary', 'date_of_birth', 'employer', 'job_title',
            'monthly_income', 'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'previous_address',
            'previous_landlord_name', 'previous_landlord_phone',
            'status', 'notes', 'created_at', 'updated_at'
        ]


class TenantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating tenants."""

    class Meta:
        model = Tenant
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'phone_secondary',
            'date_of_birth', 'employer', 'job_title', 'monthly_income',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'previous_address',
            'previous_landlord_name', 'previous_landlord_phone',
            'status', 'notes'
        ]
