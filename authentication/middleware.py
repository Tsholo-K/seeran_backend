from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


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
