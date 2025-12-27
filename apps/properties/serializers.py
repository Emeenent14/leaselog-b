"""
Serializers for properties app.
"""
from rest_framework import serializers
from .models import Property, Unit, PropertyPhoto


class UnitSerializer(serializers.ModelSerializer):
    """Serializer for units."""

    class Meta:
        model = Unit
        fields = [
            'id', 'unit_number', 'floor', 'bedrooms', 'bathrooms',
            'square_feet', 'market_rent', 'status', 'features', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PropertyPhotoSerializer(serializers.ModelSerializer):
    """Serializer for property photos."""

    class Meta:
        model = PropertyPhoto
        fields = ['id', 'url', 'caption', 'is_primary', 'sort_order']
        read_only_fields = ['id']


class PropertyListSerializer(serializers.ModelSerializer):
    """Serializer for property list view."""

    occupancy_status = serializers.CharField(read_only=True)
    primary_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'street_address', 'unit_number', 'city', 'state', 'zip_code',
            'property_type', 'is_multi_unit', 'bedrooms', 'bathrooms',
            'status', 'occupancy_status', 'primary_photo_url', 'created_at'
        ]

    def get_primary_photo_url(self, obj):
        photo = obj.photos.filter(is_primary=True).first()
        if photo:
            return photo.url
        photo = obj.photos.first()
        return photo.url if photo else None


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Serializer for property detail view."""

    occupancy_status = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    units = UnitSerializer(many=True, read_only=True)
    photos = PropertyPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            'id', 'street_address', 'unit_number', 'city', 'state', 'zip_code',
            'full_address', 'property_type', 'is_multi_unit',
            'bedrooms', 'bathrooms', 'square_feet', 'lot_size', 'year_built',
            'purchase_price', 'purchase_date', 'current_value',
            'has_mortgage', 'mortgage_balance', 'mortgage_payment', 'mortgage_lender',
            'insurance_provider', 'insurance_policy_number', 'insurance_premium',
            'insurance_renewal_date', 'status', 'occupancy_status', 'notes',
            'units', 'photos', 'created_at', 'updated_at'
        ]


class PropertyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating properties."""

    class Meta:
        model = Property
        fields = [
            'street_address', 'unit_number', 'city', 'state', 'zip_code',
            'property_type', 'is_multi_unit',
            'bedrooms', 'bathrooms', 'square_feet', 'lot_size', 'year_built',
            'purchase_price', 'purchase_date', 'current_value',
            'has_mortgage', 'mortgage_balance', 'mortgage_payment', 'mortgage_lender',
            'insurance_provider', 'insurance_policy_number', 'insurance_premium',
            'insurance_renewal_date', 'status', 'notes'
        ]

    def validate_state(self, value):
        """Ensure state is uppercase 2-letter code."""
        if len(value) != 2:
            raise serializers.ValidationError("State must be a 2-letter code.")
        return value.upper()
