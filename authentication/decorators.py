from django.http import JsonResponse
from .models import CustomUser
from rest_framework_simplejwt.tokens import AccessToken

# django
from django.core.exceptions import ObjectDoesNotExist

# utility functions 
from .utils import validate_access_token, refresh_access_token

def token_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return JsonResponse({'error': 'missing refresh token'}, status=400)
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
                return JsonResponse({"error": "invalid credentials/tokens"})
        else:
            return JsonResponse({'Error': 'Invalid tokens'}, status=406)

        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
