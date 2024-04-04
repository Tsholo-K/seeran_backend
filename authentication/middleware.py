from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.core.cache import cache
from rest_framework.response import Response
import json
from rest_framework import status


class TokenValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract the access token and refresh token from the request (e.g., from cookies)
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')
        if access_token:
            try:
                # Validate the access token
                AccessToken(access_token).verify()
            except TokenError:
                # Access token is invalid or expired
                # Check if there's a refresh token
                if not refresh_token or cache.get(refresh_token):
                    # No refresh token or refresh token blacklisted
                    # Delete both access and refresh token cookies
                    response = Response({ "error" : "invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
                    response.delete_cookie('access_token', domain='.seeran-grades.com')
                    response.delete_cookie('refresh_token', domain='.seeran-grades.com')
                    return response
                try:
                    # Attempt to refresh the token using the refresh token
                    refresh = RefreshToken(refresh_token)
                    refreshed_access_token = str(refresh.access_token)
                    # Set the new access token in the cookie
                    response = self.get_response(request)
                    response.set_cookie('access_token', refreshed_access_token, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
                    return response
                except TokenError:
                    # Refresh token is invalid or expired
                    # Delete both access and refresh token cookies
                    response = Response({ "error" : "invalid refresh tkoen"}, status=status.HTTP_401_UNAUTHORIZED)
                    response.delete_cookie('access_token', domain='.seeran-grades.com')
                    response.delete_cookie('refresh_token', domain='.seeran-grades.com')
                    return response
        # No access token present or access token is valid
        response = self.get_response(request)
        return response
    

# rate limit middleware
class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for resend otp requests
        if request.path == '/api/auth/resendotp/' or '/api/auth/signin/':
            # Implement rate limiting logic
            # For example, using Django's cache framework
            # You can adjust the rate limit and key as needed
            rate_limit = 5  # Requests per hour
            body_unicode = request.body.decode('utf-8')
            
            try:
                body_data = json.loads(body_unicode)
            except json.JSONDecodeError:
                return Response({'error': 'Invalid JSON'})
            
            email = body_data.get('email')

            if email is None:
                return Response({'error': 'Email is required'})

            cache_key = f'rate_limit:{email}'

            request_count = cache.get(cache_key, 0)
            if request_count >= rate_limit:
                return Response({'error': 'Rate limit exceeded. Please try again in 1 hour.'})

            # Increment the request count and set expiry
            cache.set(cache_key, request_count + 1, timeout=3600)  # 3600 seconds = 1 hour

        # Pass the request to the next middleware or view
        return self.get_response(request)

