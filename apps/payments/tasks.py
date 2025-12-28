"""
Celery tasks for payment reminders and notifications.
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_rent_reminders():
    """Send rent reminders 5 days before due date."""
    from .models import RentPayment
    from apps.leases.models import Lease

    reminder_date = timezone.now().date() + timedelta(days=5)

    pending_payments = RentPayment.objects.filter(
        due_date=reminder_date,
        status='pending',
        lease__status='active',
        lease__is_deleted=False
    ).select_related('lease__tenant', 'lease__rental_property', 'lease__owner')

    for payment in pending_payments:
        tenant = payment.lease.tenant
        owner = payment.lease.owner

        # Check if owner wants to send reminders
        try:
            if not owner.settings.email_rent_reminders:
                continue
        except:
            pass

        if tenant.email:
            try:
                send_mail(
                    subject=f'Rent Reminder - Due {payment.due_date.strftime("%B %d, %Y")}',
                    message=f"""
Hello {tenant.first_name},

This is a friendly reminder that your rent payment of ${payment.amount_due} is due on {payment.due_date.strftime("%B %d, %Y")}.

Property: {payment.lease.rental_property.name}

Please ensure your payment is submitted on time to avoid any late fees.

Thank you,
{owner.company_name or owner.full_name}
                    """.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.email],
                    fail_silently=True,
                )
                logger.info(f"Sent rent reminder to {tenant.email}")
            except Exception as e:
                logger.error(f"Failed to send rent reminder to {tenant.email}: {e}")

    return f"Sent reminders for {pending_payments.count()} payments"


@shared_task
def send_rent_due_notices():
    """Send notices on rent due date."""
    from .models import RentPayment

    today = timezone.now().date()

    due_payments = RentPayment.objects.filter(
        due_date=today,
        status='pending',
        lease__status='active',
        lease__is_deleted=False
    ).select_related('lease__tenant', 'lease__rental_property', 'lease__owner')

    for payment in due_payments:
        tenant = payment.lease.tenant

        if tenant.email:
            try:
                send_mail(
                    subject=f'Rent Due Today - ${payment.amount_due}',
                    message=f"""
Hello {tenant.first_name},

Your rent payment of ${payment.amount_due} is due today.

Property: {payment.lease.rental_property.name}

Please submit your payment to avoid late fees.

Thank you
                    """.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.email],
                    fail_silently=True,
                )
                logger.info(f"Sent due notice to {tenant.email}")
            except Exception as e:
                logger.error(f"Failed to send due notice to {tenant.email}: {e}")

    return f"Sent due notices for {due_payments.count()} payments"


@shared_task
def send_late_notices():
    """Send late notices after grace period."""
    from .models import RentPayment

    today = timezone.now().date()

    # Find payments that are overdue and haven't had late notice sent
    late_payments = RentPayment.objects.filter(
        status__in=['pending', 'partial'],
        due_date__lt=today,
        lease__status='active',
        lease__is_deleted=False
    ).select_related('lease__tenant', 'lease__rental_property', 'lease__owner', 'lease')

    for payment in late_payments:
        lease = payment.lease
        grace_days = lease.late_fee_grace_days
        days_overdue = (today - payment.due_date).days

        # Only send if past grace period
        if days_overdue <= grace_days:
            continue

        tenant = lease.tenant

        if tenant.email:
            try:
                send_mail(
                    subject=f'Late Rent Notice - Payment Overdue',
                    message=f"""
Hello {tenant.first_name},

Your rent payment of ${payment.amount_due} was due on {payment.due_date.strftime("%B %d, %Y")} and is now {days_overdue} days overdue.

Property: {lease.rental_property.name}
Balance Due: ${payment.balance_due}

Please submit your payment immediately to avoid additional fees.

Thank you
                    """.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.email],
                    fail_silently=True,
                )
                logger.info(f"Sent late notice to {tenant.email}")
            except Exception as e:
                logger.error(f"Failed to send late notice to {tenant.email}: {e}")

    return f"Processed {late_payments.count()} late payments"


@shared_task
def apply_automatic_late_fees():
    """Automatically apply late fees after grace period."""
    from .models import RentPayment

    today = timezone.now().date()

    # Find payments eligible for late fees
    overdue_payments = RentPayment.objects.filter(
        status__in=['pending', 'partial'],
        due_date__lt=today,
        late_fee_applied=0,
        late_fee_waived=False,
        lease__status='active',
        lease__is_deleted=False
    ).select_related('lease')

    applied_count = 0
    for payment in overdue_payments:
        lease = payment.lease
        days_overdue = (today - payment.due_date).days

        # Check if past grace period
        if days_overdue > lease.late_fee_grace_days:
            payment.apply_late_fee()
            applied_count += 1
            logger.info(f"Applied late fee to payment {payment.id}")

    return f"Applied late fees to {applied_count} payments"


@shared_task
def send_lease_expiry_reminders():
    """Send lease expiration reminders at 90, 60, and 30 days."""
    from apps.leases.models import Lease

    today = timezone.now().date()
    reminder_days = [90, 60, 30]

    for days in reminder_days:
        target_date = today + timedelta(days=days)

        expiring_leases = Lease.objects.filter(
            end_date=target_date,
            status='active',
            is_deleted=False
        ).select_related('tenant', 'rental_property', 'owner')

        for lease in expiring_leases:
            owner = lease.owner

            # Check if owner wants lease expiry notifications
            try:
                if not owner.settings.email_lease_expiring:
                    continue
            except:
                pass

            # Notify landlord
            try:
                send_mail(
                    subject=f'Lease Expiring in {days} Days - {lease.rental_property.name}',
                    message=f"""
Hello {owner.first_name},

The lease for {lease.tenant.full_name} at {lease.rental_property.name} will expire on {lease.end_date.strftime("%B %d, %Y")} ({days} days from now).

Tenant: {lease.tenant.full_name}
Property: {lease.rental_property.name}
Monthly Rent: ${lease.rent_amount}
Lease End Date: {lease.end_date.strftime("%B %d, %Y")}

Please consider reaching out to discuss renewal options.

Thank you,
LeaseLog
                    """.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[owner.email],
                    fail_silently=True,
                )
                logger.info(f"Sent {days}-day expiry reminder for lease {lease.id}")
            except Exception as e:
                logger.error(f"Failed to send expiry reminder: {e}")

    return f"Processed lease expiry reminders"


@shared_task
def send_payment_confirmation(payment_record_id):
    """Send payment confirmation email."""
    from .models import PaymentRecord

    try:
        payment_record = PaymentRecord.objects.select_related(
            'rent_payment__lease__tenant',
            'rent_payment__lease__rental_property',
            'rent_payment__lease__owner'
        ).get(id=payment_record_id)
    except PaymentRecord.DoesNotExist:
        return "Payment record not found"

    tenant = payment_record.rent_payment.lease.tenant
    owner = payment_record.rent_payment.lease.owner

    # Check if owner wants payment notifications
    try:
        if not owner.settings.email_payment_received:
            return "Payment notifications disabled"
    except:
        pass

    # Notify tenant
    if tenant.email:
        try:
            send_mail(
                subject=f'Payment Received - ${payment_record.amount}',
                message=f"""
Hello {tenant.first_name},

We have received your payment of ${payment_record.amount}.

Payment Date: {payment_record.payment_date.strftime("%B %d, %Y")}
Property: {payment_record.rent_payment.lease.rental_property.name}
Reference: {payment_record.reference_number or 'N/A'}

Thank you for your payment!
                """.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")

    # Notify landlord
    try:
        send_mail(
            subject=f'Payment Received from {tenant.full_name} - ${payment_record.amount}',
            message=f"""
Hello {owner.first_name},

A payment has been received from {tenant.full_name}.

Amount: ${payment_record.amount}
Payment Date: {payment_record.payment_date.strftime("%B %d, %Y")}
Property: {payment_record.rent_payment.lease.rental_property.name}
Reference: {payment_record.reference_number or 'N/A'}

Thank you,
LeaseLog
            """.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Failed to send payment notification to landlord: {e}")

    return f"Sent payment confirmation for payment {payment_record_id}"


@shared_task
def update_overdue_payment_status():
    """Update status of overdue payments."""
    from .models import RentPayment

    today = timezone.now().date()

    updated = RentPayment.objects.filter(
        status='pending',
        due_date__lt=today,
        lease__status='active',
        lease__is_deleted=False
    ).update(status='overdue')

    return f"Updated {updated} payments to overdue status"
