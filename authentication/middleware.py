from django.core.cache import cache
from rest_framework.response import Response
import json


# rate limit middleware
class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for resend otp requests
        if request.path == '/api/auth/resendotp/' or '/api/auth/signin/' or '/api/auth/login/':
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

