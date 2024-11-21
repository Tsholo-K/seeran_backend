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

# logging
import logging

# Get loggers
# emails_logger = logging.getLogger('emails_logger')


def token_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        try:
            # Get access token from cookies
            access_token = request.COOKIES.get('access_token')
            # if not access_token:
            #     return authentication_utilities.remove_authorization_cookies(JsonResponse(
            #         {'error': 'Request not authenticated.. access denied'},
            #         status=status.HTTP_401_UNAUTHORIZED
            #     ))

            # # Check if the token is blacklisted
            # if cache.get(access_token):
            #     return authentication_utilities.remove_authorization_cookies(JsonResponse(
            #         {'error': 'The provided access token has been blacklisted.. request revoked'},
            #         status=status.HTTP_400_BAD_REQUEST
            #     ))

            # Decode and verify the access token
            verified_access_token = authentication_utilities.validate_access_token(access_token)
        
            if verified_access_token == None:
                return authentication_utilities.remove_authorization_cookies(JsonResponse(
                    {'error': 'Invalid security credentials.. request revoked'},
                    status=status.HTTP_400_BAD_REQUEST
                ))

            # Calculate remaining lifespan of the token
            decoded_token = AccessToken(verified_access_token)
            expiry_timestamp = decoded_token['exp']  # Expiration time in UNIX timestamp
            current_timestamp = timezone.now().timestamp()
            remaining_lifespan = int(expiry_timestamp - current_timestamp)  # In seconds

            if remaining_lifespan <= 0:
                return authentication_utilities.remove_authorization_cookies(JsonResponse(
                    {'error': 'Could not process your request, your access credentials have expired.. request revoked'},
                    status=status.HTTP_401_UNAUTHORIZED
                ))

            # Proceed to the view
            response = view_func(request, *args, **kwargs)

            # Set the token back with the calculated lifespan
            response.set_cookie(
                'access_token',
                str(verified_access_token),
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                secure=True,
                httponly=True,
                max_age=remaining_lifespan
            )

            return response

        except Exception as e:
            # Log unexpected errors and provide a generic error response
            # emails_logger.error(f"Unexpected error in token validation: {str(e)}")
            return JsonResponse({'error': 'Could not process your request, an unexpected error occurred while trying to authenticate your access credentails. Error:' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return _wrapped_view_func




