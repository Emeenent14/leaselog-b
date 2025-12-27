"""
Serializers for accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserSettings


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        UserSettings.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError({
                'email': 'Invalid email or password.'
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'email': 'Account is disabled.'
            })

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""

    full_name = serializers.CharField(read_only=True)
    is_email_verified = serializers.BooleanField(read_only=True)
    property_limit = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'avatar_url', 'company_name', 'business_address',
            'subscription_tier', 'subscription_status',
            'is_email_verified', 'property_limit',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'subscription_tier', 'subscription_status',
            'created_at', 'updated_at'
        ]


class UserSettingsSerializer(serializers.ModelSerializer):
    """Serializer for user settings."""

    class Meta:
        model = UserSettings
        exclude = ['id', 'user', 'created_at', 'updated_at']


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    token = serializers.CharField()
    password = serializers.CharField(
        min_length=8,
        validators=[validate_password]
    )
