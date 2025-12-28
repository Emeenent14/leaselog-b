"""
Maintenance views.
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import MaintenanceRequest, MaintenanceComment, MaintenancePhoto
from .serializers import (
    MaintenanceRequestListSerializer, MaintenanceRequestDetailSerializer,
    MaintenanceRequestCreateSerializer, MaintenanceCommentSerializer,
    MaintenanceCommentCreateSerializer, MaintenancePhotoSerializer,
    MaintenanceCompleteSerializer
)
from apps.transactions.models import Transaction, TransactionCategory


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for maintenance requests."""

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'category', 'rental_property', 'tenant']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'priority', 'status', 'scheduled_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return MaintenanceRequest.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return MaintenanceRequestListSerializer
        if self.action == 'create':
            return MaintenanceRequestCreateSerializer
        return MaintenanceRequestDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Filter for open requests
        open_only = request.query_params.get('open')
        if open_only == 'true':
            queryset = queryset.filter(
                status__in=['open', 'in_progress', 'pending_parts', 'scheduled']
            )

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
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = MaintenanceRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        maintenance_request = MaintenanceRequest.objects.create(
            owner=request.user,
            **serializer.validated_data
        )

        return Response({
            'success': True,
            'data': MaintenanceRequestDetailSerializer(maintenance_request).data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = MaintenanceRequestCreateSerializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)

        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return Response({
            'success': True,
            'data': MaintenanceRequestDetailSerializer(instance).data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'success': True,
            'message': 'Maintenance request deleted'
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark maintenance request as completed."""
        maintenance_request = self.get_object()
        serializer = MaintenanceCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        maintenance_request.status = 'completed'
        maintenance_request.completed_at = timezone.now()
        maintenance_request.resolution_notes = data.get('resolution_notes', '')

        if data.get('actual_cost'):
            maintenance_request.actual_cost = data['actual_cost']

        # Create expense transaction if requested
        if data.get('create_expense') and maintenance_request.actual_cost:
            category = None
            if data.get('expense_category_id'):
                category = TransactionCategory.objects.filter(
                    id=data['expense_category_id']
                ).first()

            if not category:
                category = TransactionCategory.objects.filter(
                    name__icontains='repairs',
                    type='expense',
                    is_system=True
                ).first()

            transaction = Transaction.objects.create(
                owner=request.user,
                type='expense',
                category=category,
                property=maintenance_request.rental_property,
                unit=maintenance_request.unit,
                amount=maintenance_request.actual_cost,
                date=timezone.now().date(),
                description=f"Maintenance: {maintenance_request.title}",
                vendor=maintenance_request.vendor_name,
            )

            maintenance_request.expense_transaction = transaction

        maintenance_request.save()

        return Response({
            'success': True,
            'data': MaintenanceRequestDetailSerializer(maintenance_request).data
        })

    @action(detail=True, methods=['post'])
    def comments(self, request, pk=None):
        """Add a comment to maintenance request."""
        maintenance_request = self.get_object()
        serializer = MaintenanceCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = MaintenanceComment.objects.create(
            request=maintenance_request,
            author_user=request.user,
            content=serializer.validated_data['content'],
            is_internal=serializer.validated_data.get('is_internal', False)
        )

        return Response({
            'success': True,
            'data': MaintenanceCommentSerializer(comment).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def photos(self, request, pk=None):
        """Upload a photo to maintenance request."""
        maintenance_request = self.get_object()

        # This would typically handle file upload
        # For now, return the expected structure
        return Response({
            'success': True,
            'data': {
                'upload_url': 'presigned-url-here',
                'photo_id': 'uuid-here',
            }
        })

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update status of maintenance request."""
        maintenance_request = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(MaintenanceRequest.STATUS_CHOICES):
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Invalid status'}
            }, status=status.HTTP_400_BAD_REQUEST)

        maintenance_request.status = new_status

        # Handle scheduling
        if new_status == 'scheduled':
            maintenance_request.scheduled_date = request.data.get('scheduled_date')
            maintenance_request.scheduled_time = request.data.get('scheduled_time')

        # Handle completion
        if new_status == 'completed':
            maintenance_request.completed_at = timezone.now()

        maintenance_request.save()

        return Response({
            'success': True,
            'data': MaintenanceRequestDetailSerializer(maintenance_request).data
        })
