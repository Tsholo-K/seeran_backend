# python 
import time

# settings
from django.conf import settings

# django
from django.utils import timezone
from django.http import JsonResponse
from django.core.cache import cache

# rest framework
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

# utility functions 
from authentication import utils as authentication_utilities

# models
from accounts.models import BaseAccount

# logging
import logging

# Get loggers
# emails_logger = logging.getLogger('emails_logger')


def token_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        try:
            # Get access token from cookies
            access_token = request.COOKIES.get('access_token')
            if not access_token:
                return authentication_utilities.remove_authorization_cookies(JsonResponse(
                    {'error': 'Request not authenticated.. access denied'},
                    status=status.HTTP_401_UNAUTHORIZED
                ))

            # Check if the token is blacklisted
            if cache.get(access_token):
                return authentication_utilities.remove_authorization_cookies(JsonResponse(
                    {'error': 'The provided access token has been blacklisted.. request revoked'},
                    status=status.HTTP_400_BAD_REQUEST
                ))

            # Decode and verify the access token
            verified_access_token = authentication_utilities.validate_access_token(access_token)
        
            if verified_access_token == None:
                return authentication_utilities.remove_authorization_cookies(JsonResponse(
                    {'error': 'Invalid security credentials.. request revoked'},
                    status=status.HTTP_400_BAD_REQUEST
                ))

            # Calculate remaining lifespan of the token
            decoded_token = AccessToken(verified_access_token)

            # Retrieve and set the authenticated user
            try:
                requesting_account = BaseAccount.objects.get(pk=decoded_token['user_id'])
                request.user = requesting_account

            except BaseAccount.DoesNotExist:
                return authentication_utilities.remove_authorization_cookies(JsonResponse(
                    {'error': 'Could not process your request, an account with the provided access credentials does not exist.. request revoked'},
                    status=status.HTTP_401_UNAUTHORIZED
                ))

            # Proceed to the view
            return view_func(request, *args, **kwargs)

        except Exception as e:
            # Log unexpected errors and provide a generic error response
            # emails_logger.error(f"Unexpected error in token validation: {str(e)}")
            return JsonResponse({'error': 'Could not process your request, an unexpected error occurred while trying to authenticate your access credentails. Error:' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return _wrapped_view_func




