# simlpe jwt
from rest_framework_simplejwt.tokens import AccessToken

# channels
from channels.db import database_sync_to_async

# djnago
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
