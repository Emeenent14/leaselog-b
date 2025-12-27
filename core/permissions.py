"""
Custom permissions for LeaseLog API.
"""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners to access their objects.
    """

    def has_object_permission(self, request, view, obj):
        # Check if object has owner attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'owner_id'):
            return obj.owner_id == request.user.id
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to allow read-only for non-owners.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False
