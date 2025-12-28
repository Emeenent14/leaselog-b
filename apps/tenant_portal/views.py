"""
Tenant portal views.
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import TenantPortalAccess, TenantPortalSession
from .serializers import (
    TenantPortalAccessSerializer, TenantPortalLoginSerializer,
    TenantPortalSessionSerializer, TenantProfileSerializer,
    TenantLeaseSerializer, TenantPaymentSerializer,
    TenantMakePaymentSerializer, TenantMaintenanceRequestSerializer,
    TenantMaintenanceCommentSerializer
)
from apps.payments.models import RentPayment
from apps.leases.models import Lease
from apps.maintenance.models import MaintenanceRequest, MaintenanceComment


class TenantPortalAuthMixin:
    """Mixin to handle tenant portal authentication."""

    def get_portal_session(self, request):
        """Get valid portal session from request."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('TenantPortal '):
            return None

        token = auth_header.replace('TenantPortal ', '')
        try:
            session = TenantPortalSession.objects.select_related(
                'portal_access__tenant'
            ).get(
                session_token=token,
                expires_at__gt=timezone.now()
            )
            if session.portal_access.is_valid:
                return session
        except TenantPortalSession.DoesNotExist:
            pass

        return None


class TenantPortalLoginView(APIView):
    """Tenant portal login."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TenantPortalLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            portal_access = TenantPortalAccess.objects.select_related('tenant').get(
                access_token=token
            )
        except TenantPortalAccess.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired access link'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not portal_access.is_valid:
            return Response({
                'success': False,
                'error': {'code': 'EXPIRED_TOKEN', 'message': 'Access link has expired'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Create session
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session = TenantPortalSession.create_session(
            portal_access, ip_address, user_agent
        )

        return Response({
            'success': True,
            'data': TenantPortalSessionSerializer(session).data
        })


class TenantPortalProfileView(APIView, TenantPortalAuthMixin):
    """Tenant profile view."""

    permission_classes = [AllowAny]

    def get(self, request):
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        tenant = session.portal_access.tenant
        data = {
            'id': str(tenant.id),
            'first_name': tenant.first_name,
            'last_name': tenant.last_name,
            'email': tenant.email,
            'phone': tenant.phone,
        }

        return Response({
            'success': True,
            'data': data
        })


class TenantPortalLeaseView(APIView, TenantPortalAuthMixin):
    """Tenant's current lease view."""

    permission_classes = [AllowAny]

    def get(self, request):
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not session.portal_access.can_view_lease:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Not permitted to view lease'}
            }, status=status.HTTP_403_FORBIDDEN)

        tenant = session.portal_access.tenant

        # Get active lease
        lease = Lease.objects.filter(
            tenant=tenant,
            status='active',
            is_deleted=False
        ).select_related('rental_property', 'unit').first()

        if not lease:
            return Response({
                'success': True,
                'data': None
            })

        data = {
            'id': str(lease.id),
            'property_name': lease.rental_property.name,
            'property_address': lease.rental_property.address,
            'unit_name': lease.unit.name if lease.unit else None,
            'start_date': lease.start_date,
            'end_date': lease.end_date,
            'rent_amount': float(lease.rent_amount),
            'status': lease.status,
        }

        return Response({
            'success': True,
            'data': data
        })


class TenantPortalPaymentsView(APIView, TenantPortalAuthMixin):
    """Tenant's payments view."""

    permission_classes = [AllowAny]

    def get(self, request):
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not session.portal_access.can_view_payments:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Not permitted to view payments'}
            }, status=status.HTTP_403_FORBIDDEN)

        tenant = session.portal_access.tenant

        # Get payments for tenant's leases
        payments = RentPayment.objects.filter(
            lease__tenant=tenant,
            lease__is_deleted=False
        ).order_by('-due_date')[:12]

        data = []
        for payment in payments:
            data.append({
                'id': str(payment.id),
                'due_date': payment.due_date,
                'amount_due': float(payment.amount_due),
                'amount_paid': float(payment.amount_paid),
                'balance_due': float(payment.balance_due),
                'late_fee_applied': float(payment.late_fee_applied),
                'status': payment.status,
                'paid_date': payment.paid_date,
            })

        return Response({
            'success': True,
            'data': data
        })


class TenantPortalMakePaymentView(APIView, TenantPortalAuthMixin):
    """Make a payment from tenant portal."""

    permission_classes = [AllowAny]

    def post(self, request):
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not session.portal_access.can_make_payments:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Not permitted to make payments'}
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = TenantMakePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tenant = session.portal_access.tenant

        # Verify rent payment belongs to tenant
        try:
            rent_payment = RentPayment.objects.get(
                id=data['rent_payment_id'],
                lease__tenant=tenant,
                lease__is_deleted=False
            )
        except RentPayment.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Payment not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        # Here you would create a Stripe payment intent
        # For now, return success structure
        return Response({
            'success': True,
            'data': {
                'client_secret': 'stripe-client-secret',
                'payment_intent_id': 'pi_xxx',
            }
        })


class TenantPortalMaintenanceView(APIView, TenantPortalAuthMixin):
    """Tenant maintenance requests view."""

    permission_classes = [AllowAny]

    def get(self, request):
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not session.portal_access.can_submit_maintenance:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Not permitted to view maintenance'}
            }, status=status.HTTP_403_FORBIDDEN)

        tenant = session.portal_access.tenant

        requests = MaintenanceRequest.objects.filter(
            tenant=tenant
        ).order_by('-created_at')[:20]

        data = []
        for req in requests:
            data.append({
                'id': str(req.id),
                'title': req.title,
                'description': req.description,
                'category': req.category,
                'priority': req.priority,
                'status': req.status,
                'permission_to_enter': req.permission_to_enter,
                'preferred_times': req.preferred_times,
                'created_at': req.created_at,
            })

        return Response({
            'success': True,
            'data': data
        })

    def post(self, request):
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not session.portal_access.can_submit_maintenance:
            return Response({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Not permitted to submit maintenance'}
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = TenantMaintenanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tenant = session.portal_access.tenant

        # Get tenant's active lease to find property
        lease = Lease.objects.filter(
            tenant=tenant,
            status='active',
            is_deleted=False
        ).first()

        if not lease:
            return Response({
                'success': False,
                'error': {'code': 'NO_ACTIVE_LEASE', 'message': 'No active lease found'}
            }, status=status.HTTP_400_BAD_REQUEST)

        maintenance_request = MaintenanceRequest.objects.create(
            owner=lease.owner,
            rental_property=lease.rental_property,
            unit=lease.unit,
            tenant=tenant,
            submitted_by_tenant=True,
            title=data['title'],
            description=data['description'],
            category=data['category'],
            priority=data.get('priority', 'medium'),
            permission_to_enter=data.get('permission_to_enter', False),
            preferred_times=data.get('preferred_times', ''),
        )

        return Response({
            'success': True,
            'data': {
                'id': str(maintenance_request.id),
                'title': maintenance_request.title,
                'status': maintenance_request.status,
                'created_at': maintenance_request.created_at,
            }
        }, status=status.HTTP_201_CREATED)


class TenantPortalMaintenanceDetailView(APIView, TenantPortalAuthMixin):
    """Tenant maintenance request detail view."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        tenant = session.portal_access.tenant

        try:
            maintenance_request = MaintenanceRequest.objects.get(
                id=pk,
                tenant=tenant
            )
        except MaintenanceRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Request not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        # Get comments (exclude internal ones)
        comments = MaintenanceComment.objects.filter(
            request=maintenance_request,
            is_internal=False
        ).order_by('created_at')

        comment_data = [{
            'id': str(c.id),
            'content': c.content,
            'author_name': c.author_name,
            'is_landlord': c.author_user is not None,
            'created_at': c.created_at,
        } for c in comments]

        return Response({
            'success': True,
            'data': {
                'id': str(maintenance_request.id),
                'title': maintenance_request.title,
                'description': maintenance_request.description,
                'category': maintenance_request.category,
                'priority': maintenance_request.priority,
                'status': maintenance_request.status,
                'scheduled_date': maintenance_request.scheduled_date,
                'scheduled_time': str(maintenance_request.scheduled_time) if maintenance_request.scheduled_time else None,
                'comments': comment_data,
                'created_at': maintenance_request.created_at,
            }
        })

    def post(self, request, pk):
        """Add a comment to maintenance request."""
        session = self.get_portal_session(request)
        if not session:
            return Response({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Invalid session'}
            }, status=status.HTTP_401_UNAUTHORIZED)

        tenant = session.portal_access.tenant

        try:
            maintenance_request = MaintenanceRequest.objects.get(
                id=pk,
                tenant=tenant
            )
        except MaintenanceRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Request not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = TenantMaintenanceCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = MaintenanceComment.objects.create(
            request=maintenance_request,
            author_tenant=tenant,
            content=serializer.validated_data['content'],
            is_internal=False
        )

        return Response({
            'success': True,
            'data': {
                'id': str(comment.id),
                'content': comment.content,
                'created_at': comment.created_at,
            }
        }, status=status.HTTP_201_CREATED)


# Landlord views for managing portal access

class TenantPortalAccessView(APIView):
    """Landlord view to manage tenant portal access."""

    def get(self, request, tenant_id):
        """Get portal access for a tenant."""
        try:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.get(id=tenant_id, owner=request.user)
        except:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Tenant not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            portal_access = TenantPortalAccess.objects.get(tenant=tenant)
            return Response({
                'success': True,
                'data': TenantPortalAccessSerializer(portal_access).data
            })
        except TenantPortalAccess.DoesNotExist:
            return Response({
                'success': True,
                'data': None
            })

    def post(self, request, tenant_id):
        """Create or refresh portal access for a tenant."""
        try:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.get(id=tenant_id, owner=request.user)
        except:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Tenant not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        portal_access = TenantPortalAccess.create_for_tenant(tenant)

        return Response({
            'success': True,
            'data': TenantPortalAccessSerializer(portal_access).data
        })

    def delete(self, request, tenant_id):
        """Revoke portal access for a tenant."""
        try:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.get(id=tenant_id, owner=request.user)
        except:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Tenant not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        TenantPortalAccess.objects.filter(tenant=tenant).delete()

        return Response({
            'success': True,
            'message': 'Portal access revoked'
        })
