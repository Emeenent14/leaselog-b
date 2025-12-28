"""
Celery tasks for maintenance notifications.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_maintenance_status_notification(request_id, old_status, new_status):
    """Send notification when maintenance request status changes."""
    from .models import MaintenanceRequest

    try:
        request = MaintenanceRequest.objects.select_related(
            'tenant', 'property', 'owner'
        ).get(id=request_id)
    except MaintenanceRequest.DoesNotExist:
        return "Request not found"

    tenant = request.tenant
    owner = request.owner

    status_messages = {
        'in_progress': 'Work has begun on your maintenance request.',
        'scheduled': f'Your maintenance request has been scheduled for {request.scheduled_date}.',
        'completed': 'Your maintenance request has been completed.',
        'canceled': 'Your maintenance request has been canceled.',
    }

    message = status_messages.get(new_status, f'Status updated to: {new_status}')

    # Notify tenant if they submitted the request
    if tenant and tenant.email and request.submitted_by_tenant:
        try:
            send_mail(
                subject=f'Maintenance Update: {request.title}',
                message=f"""
Hello {tenant.first_name},

{message}

Request: {request.title}
Property: {request.property.name}
Status: {new_status.replace('_', ' ').title()}

{f'Resolution: {request.resolution_notes}' if new_status == 'completed' and request.resolution_notes else ''}

Thank you
                """.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.email],
                fail_silently=True,
            )
            logger.info(f"Sent maintenance update to tenant {tenant.email}")
        except Exception as e:
            logger.error(f"Failed to send maintenance update: {e}")

    return f"Processed maintenance notification for request {request_id}"


@shared_task
def send_new_maintenance_notification(request_id):
    """Send notification when new maintenance request is submitted by tenant."""
    from .models import MaintenanceRequest

    try:
        request = MaintenanceRequest.objects.select_related(
            'tenant', 'property', 'owner'
        ).get(id=request_id)
    except MaintenanceRequest.DoesNotExist:
        return "Request not found"

    owner = request.owner

    try:
        send_mail(
            subject=f'New Maintenance Request: {request.title}',
            message=f"""
Hello {owner.first_name},

A new maintenance request has been submitted.

Title: {request.title}
Property: {request.property.name}
{f'Unit: {request.unit.name}' if request.unit else ''}
Submitted by: {request.tenant.full_name if request.tenant else 'N/A'}
Priority: {request.priority.title()}
Category: {request.category.replace('_', ' ').title()}

Description:
{request.description}

{f'Permission to Enter: Yes' if request.permission_to_enter else 'Permission to Enter: No - Please coordinate with tenant'}
{f'Preferred Times: {request.preferred_times}' if request.preferred_times else ''}

Please log in to review and respond to this request.

Thank you,
LeaseLog
            """.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=True,
        )
        logger.info(f"Sent new maintenance notification to {owner.email}")
    except Exception as e:
        logger.error(f"Failed to send maintenance notification: {e}")

    return f"Sent new maintenance notification for request {request_id}"
