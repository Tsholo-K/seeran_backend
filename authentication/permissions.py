from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import User

class CustomCookieTokenPermission(BasePermission):
    """
    Custom permission class to validate JWT token from a cookie.
    """

    def has_permission(self, request, view):
        # Get the access token from the cookie
        access_token = request.COOKIES.get('access_token')

        if access_token:
            try:
                # Decode the access token
                token = AccessToken(access_token)
                # Get the user ID from the token payload
                user_id = token.payload.get('user_id')
                # Look up the user
                user = User.objects.get(id=user_id)
                # If the user exists, grant permission
                return user is not None
            except Exception:
                # Invalid token or user not found
                return False
        else:
            # No access token provided
            return False

