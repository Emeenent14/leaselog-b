"""
URL routes for accounts app.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    UserMeView,
    UserSettingsView,
    VerifyEmailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Email verification
    path('auth/email/verify/', VerifyEmailView.as_view(), name='verify_email'),

    # Password reset
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password/confirm/', PasswordResetConfirmView.as_view(), name='password_confirm'),

    # User
    path('users/me/', UserMeView.as_view(), name='user_me'),
    path('users/me/settings/', UserSettingsView.as_view(), name='user_settings'),
]
