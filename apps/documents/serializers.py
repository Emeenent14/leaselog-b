"""
Document serializers.
"""
from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents."""

    file_extension = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_pdf = serializers.ReadOnlyField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'name', 'description', 'type', 'file_name', 'file_size',
            'content_type', 'file_extension', 'is_image', 'is_pdf',
            'rental_property', 'unit', 'tenant', 'lease', 'transaction',
            'maintenance_request', 'tags', 'expiry_date', 'is_uploaded',
            'uploaded_at', 'download_url', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_key', 'file_size', 'content_type', 'is_uploaded',
            'uploaded_at', 'created_at', 'updated_at'
        ]

    def get_download_url(self, obj):
        # This would be populated by the view with a presigned URL
        return None


class DocumentCreateSerializer(serializers.Serializer):
    """Serializer for initiating document upload."""

    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=Document.TYPE_CHOICES, default='other')
    file_name = serializers.CharField(max_length=255)
    file_size = serializers.IntegerField()
    content_type = serializers.CharField(max_length=100)

    # Optional relationships
    rental_property_id = serializers.UUIDField(required=False)
    unit_id = serializers.UUIDField(required=False)
    tenant_id = serializers.UUIDField(required=False)
    lease_id = serializers.UUIDField(required=False)
    transaction_id = serializers.UUIDField(required=False)
    maintenance_request_id = serializers.UUIDField(required=False)

    tags = serializers.ListField(child=serializers.CharField(), required=False)
    expiry_date = serializers.DateField(required=False)


class UploadUrlResponseSerializer(serializers.Serializer):
    """Serializer for upload URL response."""

    document_id = serializers.UUIDField()
    upload_url = serializers.URLField()
    fields = serializers.DictField(required=False)  # For S3 form data


class DocumentConfirmSerializer(serializers.Serializer):
    """Serializer for confirming document upload."""

    pass  # No additional fields needed


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document lists."""

    class Meta:
        model = Document
        fields = [
            'id', 'name', 'type', 'file_name', 'file_size', 'content_type',
            'rental_property', 'tenant', 'lease', 'created_at'
        ]
