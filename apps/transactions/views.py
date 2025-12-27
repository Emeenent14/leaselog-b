"""
Views for transactions app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q

from core.permissions import IsOwner
from .models import Transaction, TransactionCategory
from .serializers import (
    TransactionListSerializer,
    TransactionDetailSerializer,
    TransactionCreateSerializer,
    TransactionCategorySerializer,
)


class TransactionCategoryView(APIView):
    """View for listing transaction categories."""

    def get(self, request):
        # Get system categories and user's custom categories
        categories = TransactionCategory.objects.filter(
            Q(is_system=True) | Q(owner=request.user)
        )
        serializer = TransactionCategorySerializer(categories, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for transactions."""

    permission_classes = [IsOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'category', 'property', 'tax_year', 'is_imported']
    search_fields = ['description', 'vendor_name', 'notes']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']

    def get_queryset(self):
        queryset = Transaction.objects.filter(owner=self.request.user, is_deleted=False)

        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return TransactionListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return TransactionCreateSerializer
        return TransactionDetailSerializer

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

        detail_serializer = TransactionDetailSerializer(serializer.instance)
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

        detail_serializer = TransactionDetailSerializer(instance)
        return Response({
            'success': True,
            'data': detail_serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return Response({
            'success': True,
            'data': {'message': 'Transaction has been deleted.'}
        })
