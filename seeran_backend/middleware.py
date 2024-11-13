# django
import time
import re

# simlpe jwt
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework import status

# channels
from channels.db import database_sync_to_async

# djnago
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache

# models
from accounts.models import BaseAccount

# utility functions
from authentication.utils import validate_access_token


class TokenAuthMiddleware:
    """
    Middleware for WebSocket authentication using JWT tokens stored in cookies.

    This middleware extracts the JWT token from the cookie, validates it, 
    and attaches the authenticated user and their role to the WebSocket scope.

    Attributes:
        app (ASGI application): The ASGI application instance.
    """

    def __init__(self, app):
        """
        Initializes the middleware with the ASGI application.

        Args:
            app (ASGI application): The ASGI application instance.
        """
        self.app = app

    @database_sync_to_async
    def get_account(self, account_id):
        """
        Fetches the user's account ID and role from the database.

        Args:
            user_id (int): The ID of the user to fetch.

        Returns:
            tuple: A tuple containing the user's account ID and role.

        Raises:
            CustomUser.DoesNotExist: If the user does not exist.
        """
        account = BaseAccount.objects.values('account_id', 'role').get(id=account_id)
        return (str(account['account_id']), account['role'])

    async def __call__(self, scope, receive, send):
        """
        Handles the WebSocket connection, authenticating the user via JWT token.

        Args:
            scope (dict): The connection scope.
            receive (callable): The receive function to get messages from the client.
            send (callable): The send function to send messages to the client.
        """
        headers = dict(scope['headers'])

        # Default to None for unauthenticated users
        scope['account'] = None
        scope['role'] = None
        scope['authentication_error'] = None

        # Check if the 'cookie' header is present
        if b'cookie' in headers:
            try:
                # Decode the cookies
                cookies = headers[b'cookie'].decode()
                cookie_dict = {k: v for k, v in (cookie.split('=') for cookie in cookies.split('; '))}
                # Retrieve the access token from the cookies
                access_token = cookie_dict.get('access_token')

                # Check if the access token is in cache (indicating it might be invalid/blacklisted)
                if not access_token:
                    # Handle unauthorized roles
                    scope['path'] = '/ws/authentication-error/'
                    scope['authentication_error'] = 'Could not process your request, no access token was provided.'
                    return await self.app(scope, receive, send)
                
                elif cache.get(access_token):
                    # Handle unauthorized roles
                    scope['path'] = '/ws/authentication-error/'
                    scope['authentication_error'] = 'Could not process your request, your access token has been blacklisted and cannot be used to access the system.'
                    return await self.app(scope, receive, send)

                # Validate the access token
                authorized = validate_access_token(access_token)

                # If the token is not valid, send an error message
                if authorized is None:
                    # Handle unauthorized roles
                    scope['path'] = '/ws/authentication-error/'
                    scope['authentication_error'] = 'Could not process your request, your access token has expired.'
                    return await self.app(scope, receive, send)

                # Decode the access token to get the user ID
                decoded_token = AccessToken(access_token)
                # Fetch the user and their role from the database
                scope['account'], scope['role'] = await self.get_account(decoded_token['user_id'])
                scope['access_token'] = access_token

                # Redirect based on user role
                if scope['role'] == 'FOUNDER':
                    scope['path'] = '/ws/founder/'  # Change path for FOUNDER role
                elif scope['role'] in ['PRINCIPAL', 'ADMIN']:
                    scope['path'] = '/ws/admin/'  # Change path for ADMIN role
                elif scope['role'] == 'TEACHER':
                    scope['path'] = '/ws/teacher/'  # Change path for TEACHER role
                elif scope['role'] == 'STUDENT':
                    scope['path'] = '/ws/student/'  # Change path for STUDENT role
                elif scope['role'] == 'PARENT':
                    scope['path'] = '/ws/parent/'  # Change path for PARENT role

                # Call the next application/middleware in the stack
                return await self.app(scope, receive, send)

            except BaseAccount.DoesNotExist:
                # If the user does not exist, close the connection
                # Handle unauthorized roles
                scope['path'] = '/ws/authentication-error/'
                scope['authentication_error'] = 'An account with the provided credentials does not exists. Please review you account details and try again.'
                return await self.app(scope, receive, send)

            # If any other exception occurs, close the connection and send the error message
            except Exception as e:
                # Handle unauthorized roles
                scope['path'] = '/ws/authentication-error/'
                scope['authentication_error'] = str(e)
                return await self.app(scope, receive, send)

        # Handle unauthorized roles
        scope['path'] = '/ws/authentication-error/'
        scope['authentication_error'] = 'Could not process your request, no access token was provided.'
        # Call the next application/middleware in the stack
        return await self.app(scope, receive, send)


class AuthenticationEndpointsIPThrottlingMiddleware:
    """
    Custom middleware for rate-limiting requests based on IP address for specific endpoints.
    This middleware allows only a specified number of requests (e.g., 5 requests) 
    from an IP address within a given time window (e.g., 1 hour) for the following endpoints:
    - /api/auth/login/
    - /api/auth/account-activation-credentials-verification/
    - /api/auth/password-reset-email-verification/

    Configuration:
    - rate_limit: Maximum number of requests allowed per IP within the time window.
    - time_window: The time window (in seconds) within which the requests are counted.
    """
    
    # Configuration: Max requests allowed and the time window in seconds (1 hour = 3600 seconds)
    rate_limit = 5  # Max number of requests allowed within the time window
    time_window = 3600  # Time window for rate-limiting in seconds (1 hour = 3600 seconds)

    # List of endpoints to apply the rate-limiting middleware
    target_endpoints = [
        '/api/auth/login/',
        '/api/auth/account-activation-credentials-verification/',
        '/api/auth/password-reset-email-verification/'
    ]

    def __init__(self, get_response):
        """
        Initialize the middleware with the 'get_response' callable.
        The 'get_response' will be used to call the next middleware or view.

        Args:
            get_response (callable): The next callable in the middleware chain.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Handle the request by checking if it exceeds the rate limit for specific endpoints.

        This method is called on every request. It checks the IP address of the
        client and determines if the request exceeds the rate limit. If the
        rate limit is exceeded for one of the target endpoints, it responds with an
        error message and sets a cookie indicating when the user can retry their request.

        Args:
            request (HttpRequest): The incoming HTTP request to process.

        Returns:
            HttpResponse: The response after processing the request.
        """
        # Only apply rate-limiting for specific endpoints
        if request.path not in self.target_endpoints:
            return self.get_response(request)

        # Get the IP address of the client
        ip_address = self.get_ip_address(request)
        
        # If no IP address is found, skip the throttling logic and return the response
        if not ip_address:
            return self.get_response(request)

        # Generate a unique cache key using the IP address to track the request history
        cache_key = f"throttle_ip_address_{ip_address}"

        # Retrieve the request history (list of timestamps) from the cache
        history = cache.get(cache_key, [])
        
        # If the history is not a list (corrupted or empty), reset it to an empty list
        if not isinstance(history, list):
            history = []

        # Get the current time (in seconds since the epoch)
        now = time.time()

        # Clean the history by removing timestamps that are older than the time window
        # (e.g., keep only requests that happened in the last hour)
        history = [timestamp for timestamp in history if timestamp > (now - self.time_window)]

        # If the number of requests in the history exceeds the allowed rate limit, throttle the request
        if len(history) >= self.rate_limit:
            wait_time = now - history[0]  # Time the user needs to wait before making another request

            # Get the requested URL (endpoint) for use in the error message and cookie
            endpoint = request.path
            # Sanitize the endpoint to create a valid cookie name (avoid special characters)
            sanitized_endpoint = re.sub(r'[^a-zA-Z0-9_-]', '_', endpoint)

            # Create a response indicating that the rate limit has been exceeded
            response = JsonResponse({'error': 'Could not process your request, too many requests received from your IP address. Please try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Set a cookie to inform the user of the throttle status and provide the wait time
            response.set_cookie(
                f'throttle{sanitized_endpoint}',  # The cookie name is based on the sanitized endpoint
                f'Device throttled from sending requests to endpoint: {endpoint}',  # Cookie value with throttle message
                domain=settings.SESSION_COOKIE_DOMAIN,  # Ensure the cookie is set for the correct domain
                samesite=settings.SESSION_COOKIE_SAMESITE,  # Set the SameSite policy for security
                max_age=wait_time,  # Cookie expires after the wait time (in seconds)
                secure=True  # Ensures the cookie is only sent over HTTPS
            )
            
            # Store the updated request history in the cache
            cache.set(cache_key, history, timeout=self.time_window)
            
            # Return the response with the throttle message and the cookie
            return response

        # If the rate limit is not exceeded, allow the request to proceed
        # Add the current timestamp to the history to track the request
        history.append(now)

        # Save the updated request history back to the cache (with an expiration time of 1 hour)
        cache.set(cache_key, history, timeout=self.time_window)
        
        # Call the next middleware or the view itself
        return self.get_response(request)

    def get_ip_address(self, request):
        """
        Helper method to extract the client's IP address from the request.
        This checks both the 'X-Forwarded-For' header (for reverse proxies)
        and the 'REMOTE_ADDR' header to get the IP address.

        Args:
            request (HttpRequest): The incoming HTTP request to extract the IP address from.

        Returns:
            str: The IP address of the client, or None if not found.
        """
        # Get the 'X-Forwarded-For' header which may contain the real client IP if behind a proxy
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            # If the header exists, the first IP is the real client IP (in case of proxy)
            return x_forwarded_for.split(',')[0]
        
        # Otherwise, use the 'REMOTE_ADDR' header for the IP address
        return request.META.get('REMOTE_ADDR')


class ConnectionManager:
    """
    Manages WebSocket connections, tracking active connections by user account ID.

    This class provides methods to connect, disconnect, and send messages to active WebSocket connections.

    Attributes:
        active_connections (dict): A dictionary mapping user account IDs to lists of WebSocket connections.
    """

    def __init__(self):
        """
        Initializes the ConnectionManager with an empty dictionary for active connections.
        """
        self.active_connections = {}

    async def connect(self, account_id, websocket):
        """
        Adds a new WebSocket connection for a user.

        Args:
            account_id (str): The account ID of the user.
            websocket (WebSocket): The WebSocket connection instance.
        """
        if account_id not in self.active_connections:
            self.active_connections[account_id] = []

        self.active_connections[account_id].append(websocket)


    async def disconnect(self, account_id, websocket):
        """
        Removes a WebSocket connection for a user.

        Args:
            account_id (str): The account ID of the user.
            websocket (WebSocket): The WebSocket connection instance.
        """
        if account_id in self.active_connections:
            if websocket in self.active_connections[account_id]:
                self.active_connections[account_id].remove(websocket)
            if not self.active_connections[account_id]:
                del self.active_connections[account_id]


    def get_active_connections(self):
        """
        Returns the current active connections.

        Returns:
            dict: A dictionary of active connections.
        """
        return self.active_connections
    
    
    async def send_message(self, account_id, message):
        """
        Sends a message to all active WebSocket connections for a user.

        Args:
            account_id (str): The account ID of the user.
            message (str): The message to send.
        """
        connections = self.active_connections.get(account_id, [])
        for connection in connections:
            await connection.send(text_data=message)


# Initialize the ConnectionManager instance
connection_manager = ConnectionManager()
