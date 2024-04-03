from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.core.cache import cache
from django.http import HttpResponseForbidden, HttpResponseBadRequest


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
                # Try to refresh the token using the refresh token
                if refresh_token:
                    try:
                        # Validate the refresh token
                        refresh = RefreshToken(refresh_token)
                        access_token = str(refresh.access_token)
                        # Set the new access token in the cookie
                        response = self.get_response(request)
                        response.set_cookie('access_token', access_token, httponly=True, max_age=15 * 60)
                        # Set the access token to the user object
                        user = getattr(request, 'user', None)
                        if user:
                            user.access_token = access_token
                        return response
                    except TokenError:
                        # Refresh token is invalid or expired
                        # Handle appropriately (e.g., return HTTP 401 Unauthorized)
                        pass

        # Refresh token is valid, so set it to the user object (if available)
        user = getattr(request, 'user', None)
        if user:
            user.refresh_token = refresh_token

        response = self.get_response(request)
        return response


# rate limit middleware
class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for resend otp requests
        if request.path == '/api/auth/resendotp/':
            print("run")
            # Implement rate limiting logic
            # For example, using Django's cache framework
            # You can adjust the rate limit and key as needed
            rate_limit = 5  # Requests per hour
            email = request.POST.get('email')
            if email is None:
                return HttpResponseBadRequest('Email is required')

            cache_key = f'rate_limit:{email}'

            request_count = cache.get(cache_key, 0)
            if request_count >= rate_limit:
                return HttpResponseForbidden('Rate limit exceeded')

            # Increment the request count and set expiry
            cache.set(cache_key, request_count + 1, timeout=3600)  # 3600 seconds = 1 hour

        # Pass the request to the next middleware or view
        return self.get_response(request)

