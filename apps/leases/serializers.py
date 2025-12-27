"""
Serializers for leases app.
"""
from rest_framework import serializers
from .models import Lease, LeaseAdditionalTenant
from apps.properties.serializers import PropertyListSerializer
from apps.tenants.serializers import TenantListSerializer


class LeaseListSerializer(serializers.ModelSerializer):
    """Serializer for lease list view."""

    property_address = serializers.CharField(source='rental_property.street_address', read_only=True)
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    tenant_name = serializers.CharField(source='tenant.full_name', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lease
        fields = [
            'id', 'property_address', 'unit_number', 'tenant_name',
            'lease_type', 'start_date', 'end_date', 'rent_amount',
            'status', 'days_until_expiry', 'created_at'
        ]


class LeaseDetailSerializer(serializers.ModelSerializer):
    """Serializer for lease detail view."""

    property_detail = PropertyListSerializer(source='rental_property', read_only=True)
    tenant_detail = TenantListSerializer(source='tenant', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lease
        fields = [
            'id', 'rental_property', 'property_detail', 'unit', 'tenant', 'tenant_detail',
            'lease_type', 'start_date', 'end_date', 'status',
            'rent_amount', 'rent_due_day',
            'security_deposit', 'security_deposit_paid', 'security_deposit_paid_date',
            'late_fee_type', 'late_fee_amount', 'late_fee_grace_days',
            'auto_renew', 'renewal_term_months',
            'terminated_date', 'termination_reason', 'notes',
            'days_until_expiry', 'created_at', 'updated_at'
        ]


class LeaseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating leases."""

    class Meta:
        model = Lease
        fields = [
            'rental_property', 'unit', 'tenant',
            'lease_type', 'start_date', 'end_date',
            'rent_amount', 'rent_due_day',
            'security_deposit', 'security_deposit_paid', 'security_deposit_paid_date',
            'late_fee_type', 'late_fee_amount', 'late_fee_grace_days',
            'auto_renew', 'renewal_term_months', 'notes'
        ]

    def validate(self, attrs):
        # Ensure end date is after start date
        if attrs.get('end_date') and attrs.get('start_date'):
            if attrs['end_date'] <= attrs['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })

        # Ensure rent_due_day is valid
        rent_due_day = attrs.get('rent_due_day', 1)
        if rent_due_day < 1 or rent_due_day > 28:
            raise serializers.ValidationError({
                'rent_due_day': 'Rent due day must be between 1 and 28.'
            })

        return attrs

    def create(self, validated_data):
        lease = super().create(validated_data)
        # Set status to active if start date is today or in the past
        from django.utils import timezone
        if lease.start_date <= timezone.now().date():
            lease.status = 'active'
            lease.save()
            lease.generate_rent_schedule()
        else:
            lease.status = 'pending'
            lease.save()
        return lease
