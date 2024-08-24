# django
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache

# rest framework
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

# models
from users.models import BaseUser

# utility functions 
from .utils import validate_access_token


def token_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
   
        try:
        
            access_token = request.COOKIES.get('access_token')

            if not access_token or cache.get(access_token):
                return JsonResponse({'error': 'request not authenticated.. access denied'}, status=status.HTTP_401_UNAUTHORIZED)
        
            new_access_token = validate_access_token(access_token)
        
            if new_access_token == None:
                return JsonResponse({'error': 'invalid security credentials.. request revoked'}, status=status.HTTP_400_BAD_REQUEST)
        
            decoded_token = AccessToken(new_access_token)
            request.user = BaseUser.objects.get(pk=decoded_token['user_id'])
                
            response = view_func(request, *args, **kwargs)

            # Set the new access token in the response cookie
            response.set_cookie('access_token', new_access_token, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
    
        except ObjectDoesNotExist:
            return JsonResponse({"error": "invalid credentials.. no such user exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        return response
    return _wrapped_view_func

