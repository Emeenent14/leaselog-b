"""
Core views for LeaseLog API.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import connection


class HealthCheckView(APIView):
    """Health check endpoint."""

    permission_classes = [AllowAny]

    def get(self, request):
        # Check database connection
        db_status = 'healthy'
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception:
            db_status = 'unhealthy'

        return Response({
            'success': True,
            'data': {
                'status': 'healthy' if db_status == 'healthy' else 'degraded',
                'database': db_status,
            }
        })
