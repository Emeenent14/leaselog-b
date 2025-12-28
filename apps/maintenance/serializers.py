"""
Maintenance serializers.
"""
from rest_framework import serializers
from .models import MaintenanceRequest, MaintenanceComment, MaintenancePhoto


class MaintenancePhotoSerializer(serializers.ModelSerializer):
    """Serializer for maintenance photos."""

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MaintenancePhoto
        fields = [
            'id', 'file_name', 'file_size', 'content_type', 'caption',
            'uploaded_by_tenant', 'download_url', 'created_at'
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        return None  # Populated by view


class MaintenanceCommentSerializer(serializers.ModelSerializer):
    """Serializer for maintenance comments."""

    author_name = serializers.ReadOnlyField()
    is_landlord = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceComment
        fields = [
            'id', 'content', 'is_internal', 'author_name', 'is_landlord',
            'created_at'
        ]
        read_only_fields = ['id', 'author_name', 'is_landlord', 'created_at']

    def get_is_landlord(self, obj):
        return obj.author_user is not None


class MaintenanceCommentCreateSerializer(serializers.Serializer):
    """Serializer for creating comments."""

    content = serializers.CharField()
    is_internal = serializers.BooleanField(default=False)


class MaintenanceRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for maintenance request lists."""

    property_name = serializers.CharField(source='rental_property.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.full_name', read_only=True)
    comments_count = serializers.SerializerMethodField()
    photos_count = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceRequest
        fields = [
            'id', 'title', 'category', 'priority', 'status',
            'rental_property', 'property_name', 'unit', 'unit_name',
            'tenant', 'tenant_name', 'submitted_by_tenant',
            'scheduled_date', 'comments_count', 'photos_count',
            'created_at'
        ]

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_photos_count(self, obj):
        return obj.photos.count()


class MaintenanceRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for maintenance requests."""

    property_name = serializers.CharField(source='rental_property.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.full_name', read_only=True)
    comments = MaintenanceCommentSerializer(many=True, read_only=True)
    photos = MaintenancePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            'id', 'title', 'description', 'category', 'priority', 'status',
            'rental_property', 'property_name', 'unit', 'unit_name',
            'tenant', 'tenant_name', 'submitted_by_tenant',
            'permission_to_enter', 'preferred_times',
            'scheduled_date', 'scheduled_time',
            'completed_at', 'resolution_notes',
            'estimated_cost', 'actual_cost', 'expense_transaction',
            'vendor_name', 'vendor_phone', 'vendor_email',
            'comments', 'photos',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'submitted_by_tenant', 'completed_at',
                           'expense_transaction', 'created_at', 'updated_at']


class MaintenanceRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating maintenance requests."""

    class Meta:
        model = MaintenanceRequest
        fields = [
            'title', 'description', 'category', 'priority',
            'rental_property', 'unit', 'tenant',
            'permission_to_enter', 'preferred_times',
            'scheduled_date', 'scheduled_time',
            'estimated_cost', 'vendor_name', 'vendor_phone', 'vendor_email'
        ]


class MaintenanceCompleteSerializer(serializers.Serializer):
    """Serializer for completing a maintenance request."""

    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    actual_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    create_expense = serializers.BooleanField(default=False)
    expense_category_id = serializers.UUIDField(required=False)
