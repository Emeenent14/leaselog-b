"""
Views for leases app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from core.permissions import IsOwner
from .models import Lease
from .serializers import (
    LeaseListSerializer,
    LeaseDetailSerializer,
    LeaseCreateSerializer,
)


class LeaseViewSet(viewsets.ModelViewSet):
    """ViewSet for leases."""

    permission_classes = [IsOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'lease_type', 'rental_property', 'tenant']
    search_fields = ['rental_property__street_address', 'tenant__first_name', 'tenant__last_name']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'rent_amount']
    ordering = ['-start_date']

    def get_queryset(self):
        return Lease.objects.filter(owner=self.request.user, is_deleted=False)

    def get_serializer_class(self):
        if self.action == 'list':
            return LeaseListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return LeaseCreateSerializer
        return LeaseDetailSerializer

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

        detail_serializer = LeaseDetailSerializer(serializer.instance)
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

        detail_serializer = LeaseDetailSerializer(instance)
        return Response({
            'success': True,
            'data': detail_serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)

        return Response({
            'success': True,
            'data': {'message': 'Lease has been deleted.'}
        })

    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """Terminate a lease early."""
        lease = self.get_object()

        if lease.status != 'active':
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Only active leases can be terminated.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        termination_date = request.data.get('termination_date', timezone.now().date())
        reason = request.data.get('reason', '')

        lease.status = 'terminated'
        lease.terminated_date = termination_date
        lease.termination_reason = reason
        lease.save()

        # Update tenant status if they have no other active leases
        if not Lease.objects.filter(tenant=lease.tenant, status='active').exclude(id=lease.id).exists():
            lease.tenant.status = 'past'
            lease.tenant.save()

        # Update unit status if applicable
        if lease.unit:
            lease.unit.status = 'vacant'
            lease.unit.save()

        return Response({
            'success': True,
            'data': LeaseDetailSerializer(lease).data
        })

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """Renew a lease."""
        old_lease = self.get_object()

        if old_lease.status not in ['active', 'expired']:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_STATUS', 'message': 'Only active or expired leases can be renewed.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get renewal parameters
        term_months = request.data.get('term_months', old_lease.renewal_term_months)
        new_rent = request.data.get('rent_amount', old_lease.rent_amount)

        # Calculate new dates
        new_start = old_lease.end_date + relativedelta(days=1)
        new_end = new_start + relativedelta(months=term_months) - relativedelta(days=1)

        # Mark old lease as renewed
        old_lease.status = 'renewed'
        old_lease.save()

        # Create new lease
        new_lease = Lease.objects.create(
            owner=old_lease.owner,
            rental_property=old_lease.rental_property,
            unit=old_lease.unit,
            tenant=old_lease.tenant,
            lease_type=old_lease.lease_type,
            start_date=new_start,
            end_date=new_end,
            rent_amount=new_rent,
            rent_due_day=old_lease.rent_due_day,
            security_deposit=old_lease.security_deposit,
            security_deposit_paid=old_lease.security_deposit_paid,
            late_fee_type=old_lease.late_fee_type,
            late_fee_amount=old_lease.late_fee_amount,
            late_fee_grace_days=old_lease.late_fee_grace_days,
            auto_renew=old_lease.auto_renew,
            renewal_term_months=old_lease.renewal_term_months,
            status='active'
        )

        # Generate rent schedule for new lease
        new_lease.generate_rent_schedule()

        return Response({
            'success': True,
            'data': LeaseDetailSerializer(new_lease).data
        }, status=status.HTTP_201_CREATED)
