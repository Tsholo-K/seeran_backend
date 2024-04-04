from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed

class ValidateAccessToken(permissions.BasePermission):
    def has_permission(self, request, view):
        # Extract the access token from the request cookie
        access_token = request.COOKIES.get('access_token')
        
        if access_token:
            try:
                # Validate the access token using JWTAuthentication
                authentication = JWTAuthentication()
                user, token = authentication.authenticate_credentials(access_token)
                
                # Authentication succeeded, return True
                return True
            except InvalidToken:
                # Token is invalid, raise AuthenticationFailed with an appropriate error message
                raise AuthenticationFailed('Invalid access token')
        else:
            # No access token provided, return False
            return False
