"""
Document views for file management.
"""
import boto3
import uuid
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Document
from .serializers import (
    DocumentSerializer, DocumentListSerializer, DocumentCreateSerializer,
    UploadUrlResponseSerializer, DocumentConfirmSerializer
)


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for documents."""

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'rental_property', 'tenant', 'lease']
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['name', 'created_at', 'type']
    ordering = ['-created_at']

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentListSerializer
        if self.action == 'create':
            return DocumentCreateSerializer
        return DocumentSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = DocumentSerializer(instance)
        data = serializer.data

        # Add presigned download URL
        data['download_url'] = self._generate_download_url(instance)

        return Response({
            'success': True,
            'data': data
        })

    def create(self, request, *args, **kwargs):
        """Initiate document upload - returns presigned URL."""
        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Generate unique file key
        file_ext = data['file_name'].rsplit('.', 1)[-1] if '.' in data['file_name'] else ''
        file_key = f"documents/{request.user.id}/{uuid.uuid4()}.{file_ext}"

        # Create document record
        document = Document.objects.create(
            owner=request.user,
            name=data['name'],
            description=data.get('description', ''),
            type=data.get('type', 'other'),
            file_key=file_key,
            file_name=data['file_name'],
            file_size=data['file_size'],
            content_type=data['content_type'],
            rental_property_id=data.get('rental_property_id'),
            unit_id=data.get('unit_id'),
            tenant_id=data.get('tenant_id'),
            lease_id=data.get('lease_id'),
            transaction_id=data.get('transaction_id'),
            maintenance_request_id=data.get('maintenance_request_id'),
            tags=data.get('tags', []),
            expiry_date=data.get('expiry_date'),
            is_uploaded=False,
        )

        # Generate presigned upload URL
        upload_url = self._generate_upload_url(document)

        return Response({
            'success': True,
            'data': {
                'document_id': str(document.id),
                'upload_url': upload_url,
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm document upload is complete."""
        document = self.get_object()

        if document.is_uploaded:
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_CONFIRMED', 'message': 'Upload already confirmed'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify file exists in S3
        try:
            s3_client = self._get_s3_client()
            s3_client.head_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=document.file_key
            )
        except Exception:
            return Response({
                'success': False,
                'error': {'code': 'FILE_NOT_FOUND', 'message': 'File not found in storage'}
            }, status=status.HTTP_400_BAD_REQUEST)

        document.is_uploaded = True
        document.uploaded_at = timezone.now()
        document.save()

        return Response({
            'success': True,
            'data': DocumentSerializer(document).data
        })

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Get download URL for document."""
        document = self.get_object()

        if not document.is_uploaded:
            return Response({
                'success': False,
                'error': {'code': 'NOT_UPLOADED', 'message': 'Document not uploaded yet'}
            }, status=status.HTTP_400_BAD_REQUEST)

        download_url = self._generate_download_url(document)

        return Response({
            'success': True,
            'data': {'download_url': download_url}
        })

    def destroy(self, request, *args, **kwargs):
        """Delete document and file from storage."""
        document = self.get_object()

        # Delete from S3
        if document.is_uploaded:
            try:
                s3_client = self._get_s3_client()
                s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=document.file_key
                )
            except Exception:
                pass  # Continue with deletion even if S3 delete fails

        document.delete()

        return Response({
            'success': True,
            'message': 'Document deleted'
        })

    def _get_s3_client(self):
        """Get configured S3 client."""
        return boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
            region_name=settings.AWS_S3_REGION_NAME,
        )

    def _generate_upload_url(self, document):
        """Generate presigned URL for upload."""
        s3_client = self._get_s3_client()

        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': document.file_key,
                'ContentType': document.content_type,
            },
            ExpiresIn=3600,  # 1 hour
        )

        return url

    def _generate_download_url(self, document):
        """Generate presigned URL for download."""
        s3_client = self._get_s3_client()

        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': document.file_key,
                'ResponseContentDisposition': f'attachment; filename="{document.file_name}"',
            },
            ExpiresIn=settings.AWS_QUERYSTRING_EXPIRE,
        )

        return url
