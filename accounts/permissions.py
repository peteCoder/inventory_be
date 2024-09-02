from rest_framework.permissions import BasePermission


class IsUserVerified(BasePermission):
    """
        Allow access only to users that are verified
    """
    def has_permission(self, request, view):
        return bool(request.user.is_verified)