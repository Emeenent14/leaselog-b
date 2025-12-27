"""
Views for accounts app.
"""
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
import secrets

from .models import User, UserSettings, EmailVerificationToken, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserSettingsSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create verification token
        token = EmailVerificationToken.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(hours=24)
        )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'success': True,
            'data': {
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'message': 'Account created successfully. Please check your email to verify your account.'
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """User login endpoint."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'success': True,
            'data': {
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'expires_in': 3600,
                },
                'user': UserSerializer(user).data
            }
        })


class LogoutView(APIView):
    """User logout endpoint."""

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({
                'success': True,
                'data': {'message': 'Successfully logged out.'}
            })
        except Exception:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid token.'}
            }, status=status.HTTP_400_BAD_REQUEST)


class UserMeView(generics.RetrieveUpdateAPIView):
    """Current user profile endpoint."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
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


class UserSettingsView(generics.RetrieveUpdateAPIView):
    """User settings endpoint."""

    serializer_class = UserSettingsSerializer

    def get_object(self):
        settings, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return settings

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
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


class VerifyEmailView(APIView):
    """Email verification endpoint."""

    permission_classes = [AllowAny]

    def post(self, request):
        token_str = request.data.get('token')

        try:
            token = EmailVerificationToken.objects.get(
                token=token_str,
                used_at__isnull=True,
                expires_at__gt=timezone.now()
            )
        except EmailVerificationToken.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired token.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Mark as verified
        token.user.email_verified_at = timezone.now()
        token.user.save(update_fields=['email_verified_at'])

        token.used_at = timezone.now()
        token.save(update_fields=['used_at'])

        return Response({
            'success': True,
            'data': {'message': 'Email verified successfully.'}
        })


class PasswordResetRequestView(APIView):
    """Password reset request endpoint."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)

            # Create reset token
            token = PasswordResetToken.objects.create(
                user=user,
                token=secrets.token_urlsafe(32),
                expires_at=timezone.now() + timedelta(hours=1)
            )

            # In production, send email here
            # send_password_reset_email.delay(user.id, token.token)
        except User.DoesNotExist:
            pass  # Don't reveal if email exists

        return Response({
            'success': True,
            'data': {
                'message': 'If an account exists with this email, a reset link has been sent.'
            }
        })


class PasswordResetConfirmView(APIView):
    """Password reset confirmation endpoint."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            token = PasswordResetToken.objects.get(
                token=token_str,
                used_at__isnull=True,
                expires_at__gt=timezone.now()
            )
        except PasswordResetToken.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired token.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update password
        token.user.set_password(password)
        token.user.save()

        token.used_at = timezone.now()
        token.save(update_fields=['used_at'])

        return Response({
            'success': True,
            'data': {'message': 'Password has been reset successfully.'}
        })
