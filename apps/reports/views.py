"""
Views for reports app.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.properties.models import Property
from apps.leases.models import Lease
from apps.transactions.models import Transaction
from apps.payments.models import RentPayment


class DashboardSummaryView(APIView):
    """Dashboard summary endpoint."""

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # Properties summary
        properties = Property.objects.filter(owner=user, is_deleted=False)
        total_properties = properties.count()

        # Count occupied vs vacant
        occupied = 0
        vacant = 0
        for prop in properties:
            status = prop.occupancy_status
            if status == 'occupied':
                occupied += 1
            elif status == 'vacant':
                vacant += 1
            else:  # partial
                occupied += 1

        occupancy_rate = (occupied / total_properties * 100) if total_properties > 0 else 0

        # Income this month
        income_this_month = Transaction.objects.filter(
            owner=user,
            type='income',
            date__gte=first_of_month,
            date__lte=today,
            is_deleted=False
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        rent_income = Transaction.objects.filter(
            owner=user,
            type='income',
            date__gte=first_of_month,
            date__lte=today,
            category__name__icontains='rent',
            is_deleted=False
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        other_income = income_this_month - rent_income

        # Expenses this month
        expenses_this_month = Transaction.objects.filter(
            owner=user,
            type='expense',
            date__gte=first_of_month,
            date__lte=today,
            is_deleted=False
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Expenses by category
        expenses_by_category = Transaction.objects.filter(
            owner=user,
            type='expense',
            date__gte=first_of_month,
            date__lte=today,
            is_deleted=False,
            category__isnull=False
        ).values('category__name').annotate(
            amount=Sum('amount')
        ).order_by('-amount')[:5]

        # Rent collection
        rent_payments_due = RentPayment.objects.filter(
            lease__owner=user,
            due_date__gte=first_of_month,
            due_date__lte=today,
            lease__is_deleted=False
        )

        expected_rent = rent_payments_due.aggregate(
            total=Sum('amount_due')
        )['total'] or Decimal('0')

        collected_rent = rent_payments_due.aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0')

        collection_rate = (
            float(collected_rent / expected_rent * 100)
            if expected_rent > 0 else 100
        )

        # Upcoming alerts
        thirty_days = today + timedelta(days=30)

        expiring_leases = Lease.objects.filter(
            owner=user,
            status='active',
            end_date__lte=thirty_days,
            end_date__gte=today,
            is_deleted=False
        ).count()

        overdue_rent = RentPayment.objects.filter(
            lease__owner=user,
            status__in=['pending', 'partial'],
            due_date__lt=today,
            lease__is_deleted=False
        ).count()

        return Response({
            'success': True,
            'data': {
                'properties': {
                    'total': total_properties,
                    'occupied': occupied,
                    'vacant': vacant,
                    'occupancy_rate': round(occupancy_rate, 1),
                },
                'income': {
                    'total': float(income_this_month),
                    'rent': float(rent_income),
                    'other': float(other_income),
                },
                'expenses': {
                    'total': float(expenses_this_month),
                    'by_category': [
                        {'category': item['category__name'], 'amount': float(item['amount'])}
                        for item in expenses_by_category
                    ],
                },
                'net_operating_income': float(income_this_month - expenses_this_month),
                'rent_collection': {
                    'expected': float(expected_rent),
                    'collected': float(collected_rent),
                    'collection_rate': round(collection_rate, 1),
                },
                'upcoming': {
                    'expiring_leases': expiring_leases,
                    'overdue_rent': overdue_rent,
                    'maintenance_pending': 0,  # Phase 2
                },
            }
        })


class IncomeExpenseReportView(APIView):
    """Income vs Expense report endpoint."""

    def get(self, request):
        user = request.user

        # Get date range
        year = int(request.query_params.get('year', timezone.now().year))
        property_id = request.query_params.get('property')

        # Base queryset
        transactions = Transaction.objects.filter(
            owner=user,
            tax_year=year,
            is_deleted=False
        )

        if property_id:
            transactions = transactions.filter(property_id=property_id)

        # Income totals
        income = transactions.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        income_by_category = transactions.filter(
            type='income',
            category__isnull=False
        ).values('category__name').annotate(
            amount=Sum('amount')
        ).order_by('-amount')

        # Expense totals
        expenses = transactions.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        expenses_by_category = transactions.filter(
            type='expense',
            category__isnull=False
        ).values('category__name', 'category__schedule_e_line').annotate(
            amount=Sum('amount')
        ).order_by('-amount')

        # Monthly breakdown
        monthly_data = []
        for month in range(1, 13):
            month_income = transactions.filter(
                type='income',
                date__month=month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            month_expenses = transactions.filter(
                type='expense',
                date__month=month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            monthly_data.append({
                'month': month,
                'income': float(month_income),
                'expenses': float(month_expenses),
                'net': float(month_income - month_expenses),
            })

        return Response({
            'success': True,
            'data': {
                'year': year,
                'income': {
                    'total': float(income),
                    'by_category': [
                        {'category': item['category__name'], 'amount': float(item['amount'])}
                        for item in income_by_category
                    ],
                },
                'expenses': {
                    'total': float(expenses),
                    'by_category': [
                        {
                            'category': item['category__name'],
                            'schedule_e_line': item['category__schedule_e_line'],
                            'amount': float(item['amount'])
                        }
                        for item in expenses_by_category
                    ],
                },
                'net_operating_income': float(income - expenses),
                'monthly': monthly_data,
            }
        })
