"""
Views for payments app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone

from .models import RentPayment, PaymentRecord
from .serializers import (
    RentPaymentListSerializer,
    RentPaymentDetailSerializer,
    RecordPaymentSerializer,
)
from apps.transactions.models import Transaction, TransactionCategory


class RentPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for rent payments."""

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'lease', 'lease__rental_property']
    ordering_fields = ['due_date', 'amount_due', 'status']
    ordering = ['due_date']

    def get_queryset(self):
        queryset = RentPayment.objects.filter(
            lease__owner=self.request.user,
            lease__is_deleted=False
        )

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(due_date__lte=end_date)

        # Filter for overdue
        overdue_only = self.request.query_params.get('overdue')
        if overdue_only == 'true':
            queryset = queryset.filter(
                status__in=['pending', 'partial'],
                due_date__lt=timezone.now().date()
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return RentPaymentListSerializer
        return RentPaymentDetailSerializer

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

    @action(detail=True, methods=['post'])
    def record(self, request, pk=None):
        """Record a payment for this rent payment."""
        rent_payment = self.get_object()

        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Create payment record
        payment_record = PaymentRecord.objects.create(
            rent_payment=rent_payment,
            amount=data['amount'],
            payment_date=data['payment_date'],
            payment_method=data.get('payment_method', 'other'),
            reference_number=data.get('reference_number', ''),
            notes=data.get('notes', '')
        )

        # Create income transaction
        rent_category = TransactionCategory.objects.filter(
            name__icontains='rent',
            type='income',
            is_system=True
        ).first()

        transaction = Transaction.objects.create(
            owner=rent_payment.lease.owner,
            type='income',
            category=rent_category,
            property=rent_payment.lease.rental_property,
            unit=rent_payment.lease.unit,
            tenant=rent_payment.lease.tenant,
            lease=rent_payment.lease,
            amount=data['amount'],
            date=data['payment_date'],
            description=f"Rent payment for {rent_payment.due_date.strftime('%B %Y')}",
            payment_method=data.get('payment_method', 'other'),
            reference_number=data.get('reference_number', ''),
        )

        payment_record.transaction = transaction
        payment_record.save()

        return Response({
            'success': True,
            'data': RentPaymentDetailSerializer(rent_payment).data
        })

    @action(detail=True, methods=['post'])
    def apply_late_fee(self, request, pk=None):
        """Apply late fee to this rent payment."""
        rent_payment = self.get_object()

        if rent_payment.late_fee_applied > 0:
            return Response({
                'success': False,
                'error': {'code': 'FEE_ALREADY_APPLIED', 'message': 'Late fee has already been applied.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        rent_payment.apply_late_fee()

        return Response({
            'success': True,
            'data': RentPaymentDetailSerializer(rent_payment).data
        })

    @action(detail=True, methods=['post'])
    def waive_late_fee(self, request, pk=None):
        """Waive late fee for this rent payment."""
        rent_payment = self.get_object()

        reason = request.data.get('reason', '')

        rent_payment.late_fee_waived = True
        rent_payment.late_fee_waived_reason = reason
        rent_payment.late_fee_applied = 0
        rent_payment.save()

        return Response({
            'success': True,
            'data': RentPaymentDetailSerializer(rent_payment).data
        })
