"""
Serializers for payments app.
"""
from rest_framework import serializers
from .models import RentPayment, PaymentRecord


class PaymentRecordSerializer(serializers.ModelSerializer):
    """Serializer for payment records."""

    class Meta:
        model = PaymentRecord
        fields = [
            'id', 'amount', 'payment_date', 'payment_method',
            'reference_number', 'notes', 'created_at'
        ]


class RentPaymentListSerializer(serializers.ModelSerializer):
    """Serializer for rent payment list view."""

    tenant_name = serializers.CharField(source='lease.tenant.full_name', read_only=True)
    property_address = serializers.CharField(source='lease.property.street_address', read_only=True)
    balance_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_late = serializers.BooleanField(read_only=True)

    class Meta:
        model = RentPayment
        fields = [
            'id', 'tenant_name', 'property_address', 'due_date',
            'amount_due', 'amount_paid', 'late_fee_applied', 'balance_due',
            'status', 'is_late', 'paid_date'
        ]


class RentPaymentDetailSerializer(serializers.ModelSerializer):
    """Serializer for rent payment detail view."""

    tenant_name = serializers.CharField(source='lease.tenant.full_name', read_only=True)
    property_address = serializers.CharField(source='lease.property.street_address', read_only=True)
    balance_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_late = serializers.BooleanField(read_only=True)
    payment_records = PaymentRecordSerializer(many=True, read_only=True)

    class Meta:
        model = RentPayment
        fields = [
            'id', 'lease', 'tenant_name', 'property_address', 'due_date',
            'amount_due', 'amount_paid', 'late_fee_applied', 'late_fee_waived',
            'late_fee_waived_reason', 'balance_due', 'status', 'is_late',
            'paid_date', 'notes', 'payment_records', 'created_at', 'updated_at'
        ]


class RecordPaymentSerializer(serializers.Serializer):
    """Serializer for recording a payment."""

    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    payment_date = serializers.DateField()
    payment_method = serializers.ChoiceField(
        choices=PaymentRecord.PAYMENT_METHOD_CHOICES,
        default='other'
    )
    reference_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
