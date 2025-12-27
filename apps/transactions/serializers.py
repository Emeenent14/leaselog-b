"""
Serializers for transactions app.
"""
from rest_framework import serializers
from .models import Transaction, TransactionCategory


class TransactionCategorySerializer(serializers.ModelSerializer):
    """Serializer for transaction categories."""

    class Meta:
        model = TransactionCategory
        fields = ['id', 'name', 'type', 'schedule_e_line', 'is_system']


class TransactionListSerializer(serializers.ModelSerializer):
    """Serializer for transaction list view."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    property_address = serializers.CharField(source='property.street_address', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'type', 'category', 'category_name', 'property', 'property_address',
            'amount', 'date', 'description', 'payment_method', 'is_imported', 'created_at'
        ]


class TransactionDetailSerializer(serializers.ModelSerializer):
    """Serializer for transaction detail view."""

    category_detail = TransactionCategorySerializer(source='category', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'type', 'category', 'category_detail', 'property', 'unit',
            'tenant', 'lease', 'amount', 'date', 'description', 'payment_method',
            'reference_number', 'vendor_name', 'receipt_url', 'is_tax_deductible',
            'tax_year', 'is_imported', 'import_source', 'notes',
            'created_at', 'updated_at'
        ]


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating transactions."""

    class Meta:
        model = Transaction
        fields = [
            'type', 'category', 'property', 'unit', 'tenant', 'lease',
            'amount', 'date', 'description', 'payment_method',
            'reference_number', 'vendor_name', 'receipt_url',
            'is_tax_deductible', 'notes'
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value
