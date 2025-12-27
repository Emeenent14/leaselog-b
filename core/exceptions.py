"""
Custom exception handling for LeaseLog API.
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable.'
    default_code = 'service_unavailable'


class PaymentRequired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Payment required.'
    default_code = 'payment_required'


def custom_exception_handler(exc, context):
    """Custom exception handler with consistent format."""

    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the response format
        error_code = getattr(exc, 'default_code', 'error')
        error_message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)

        # Handle validation errors
        if isinstance(exc.detail, dict):
            details = []
            for field, messages in exc.detail.items():
                if isinstance(messages, list):
                    for message in messages:
                        details.append({'field': field, 'message': str(message)})
                else:
                    details.append({'field': field, 'message': str(messages)})

            response.data = {
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Invalid input data',
                    'details': details,
                }
            }
        else:
            response.data = {
                'success': False,
                'error': {
                    'code': error_code.upper(),
                    'message': error_message,
                }
            }
    else:
        # Handle non-DRF exceptions
        logger.exception(f"Unhandled exception: {exc}")

        from rest_framework.response import Response
        response = Response({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'An unexpected error occurred.',
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
