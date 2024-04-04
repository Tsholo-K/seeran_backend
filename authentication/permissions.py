from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework import status

class ValidateAccessToken(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            # Attempt to authenticate the user using JWTAuthentication
            authentication = JWTAuthentication()
            user, token = authentication.authenticate(request)
            
            # If authentication succeeds, the token is valid
            return True
        except InvalidToken:
            # If the token is invalid, raise AuthenticationFailed with a meaningful error message
            raise AuthenticationFailed('Invalid access token')
        except TokenError:
            # If there is any other token error, raise AuthenticationFailed with a meaningful error message
            raise AuthenticationFailed('Token error occurred')

    def handle_exception(self, exc):
        # Handle exceptions raised by has_permission method
        if isinstance(exc, AuthenticationFailed):
            # Return a meaningful error response with status code 401 Unauthorized
            return Response({'error': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            # For other exceptions, let the default exception handler handle them
            return super().handle_exception(exc)
