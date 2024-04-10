from django.http import JsonResponse
from .models import CustomUser
from rest_framework_simplejwt.tokens import AccessToken

# django
from django.core.exceptions import ObjectDoesNotExist

# utility functions 
from .utils import validate_access_token, refresh_access_token


class TokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of URLs to exclude
        excluded_urls = ['/api/auth/login/', '/api/auth/sigin/', '/api/auth/mfalogin/', '/api/auth/verifyotp/', '/api/auth/resetpassword/', '/api/auth/setpassword', 'api/auth/resendotp/', '/api/auth/otpverification/', 'api/auth/accountstatus/', 'api/auth/', 'apiauth/sns/notifications']

        # Check if the current URL is in the list of excluded URLs
        if request.path not in excluded_urls:
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
        response = self.get_response(request)
        # Set the new access token in the response cookie
        if new_access_token:
            response.set_cookie('access_token', new_access_token, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        return response
