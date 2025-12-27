"""
Views for properties app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from core.permissions import IsOwner
from .models import Property, Unit
from .serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    PropertyCreateSerializer,
    UnitSerializer,
)


class PropertyViewSet(viewsets.ModelViewSet):
    """ViewSet for properties."""

    permission_classes = [IsOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'property_type', 'is_multi_unit', 'city', 'state']
    search_fields = ['street_address', 'city']
    ordering_fields = ['created_at', 'street_address', 'city']
    ordering = ['-created_at']

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user, is_deleted=False)

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return PropertyCreateSerializer
        return PropertyDetailSerializer

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

        # Return detail serializer for created object
        detail_serializer = PropertyDetailSerializer(serializer.instance)
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

        detail_serializer = PropertyDetailSerializer(instance)
        return Response({
            'success': True,
            'data': detail_serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return Response({
            'success': True,
            'data': {'message': 'Property has been deleted.'}
        })

    @action(detail=True, methods=['get', 'post'])
    def units(self, request, pk=None):
        """List or create units for a property."""
        property_obj = self.get_object()

        if request.method == 'GET':
            units = Unit.objects.filter(property=property_obj, is_deleted=False)
            serializer = UnitSerializer(units, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            })

        elif request.method == 'POST':
            serializer = UnitSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(property=property_obj)

            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)


class UnitViewSet(viewsets.ModelViewSet):
    """ViewSet for units."""

    serializer_class = UnitSerializer

    def get_queryset(self):
        return Unit.objects.filter(
            property__owner=self.request.user,
            is_deleted=False
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'success': True,
            'data': serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()

        return Response({
            'success': True,
            'data': {'message': 'Unit has been deleted.'}
        })
