# django
from django.http import JsonResponse

# models
from users.models import CustomUser

# restframework
from rest_framework_simplejwt.tokens import AccessToken

# django
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache

# utility functions 
from .utils import validate_access_token, refresh_access_token

# rest framework
from rest_framework import status


def token_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
   
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return JsonResponse({'error': 'request not authenticated.. access denied'}, status=status.HTTP_401_UNAUTHORIZED)
   
        if cache.get(refresh_token):
            return JsonResponse({'error': 'invalid security credentials.. request revoked'}, status=status.HTTP_401_UNAUTHORIZED)
    
        if not access_token:
            new_access_token = refresh_access_token(refresh_token)
   
        else:
            new_access_token = validate_access_token(access_token)
     
            if new_access_token == None:
                new_access_token = refresh_access_token(refresh_token)

        if new_access_token:
      
            decoded_token = AccessToken(new_access_token)
            try:
                request.user = CustomUser.objects.get(pk=decoded_token['user_id'])
     
            except ObjectDoesNotExist:
                return JsonResponse({"error": "invalid credentials.. no such user exists"}, status=status.HTTP_400_BAD_REQUEST)
     
        else:
            return JsonResponse({'error': 'invalid security credentials.. request revoked'}, status=status.HTTP_400_BAD_REQUEST)

        response = view_func(request, *args, **kwargs)

        # Set the new access token in the response cookie
        if new_access_token:
            response.set_cookie('access_token', new_access_token, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        
        return response
    return _wrapped_view_func

