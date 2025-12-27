"""
Views for tenants app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from datetime import timedelta
import secrets

from core.permissions import IsOwner
from .models import Tenant
from .serializers import (
    TenantListSerializer,
    TenantDetailSerializer,
    TenantCreateSerializer,
)


class TenantViewSet(viewsets.ModelViewSet):
    """ViewSet for tenants."""

    permission_classes = [IsOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['created_at', 'last_name', 'first_name']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        return Tenant.objects.filter(owner=self.request.user, is_deleted=False)

    def get_serializer_class(self):
        if self.action == 'list':
            return TenantListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TenantCreateSerializer
        return TenantDetailSerializer

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
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        detail_serializer = TenantDetailSerializer(serializer.instance)
        return Response({
            'success': True,
            'data': detail_serializer.data
        }, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        detail_serializer = TenantDetailSerializer(instance)
        return Response({
            'success': True,
            'data': detail_serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return Response({
            'success': True,
            'data': {'message': 'Tenant has been deleted.'}
        })

    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """Generate portal invitation token."""
        tenant = self.get_object()

        # Generate new token
        tenant.portal_token = secrets.token_urlsafe(32)
        tenant.portal_token_expires = timezone.now() + timedelta(days=7)
        tenant.save(update_fields=['portal_token', 'portal_token_expires'])

        return Response({
            'success': True,
            'data': {
                'message': 'Invitation generated.',
                'portal_url': f"{request.build_absolute_uri('/')[:-1]}/tenant-portal/{tenant.portal_token}"
            }
        })
