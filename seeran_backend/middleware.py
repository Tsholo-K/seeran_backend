# python
import json

from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from users.models import CustomUser
from rest_framework_simplejwt.tokens import AccessToken
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
    def get_user(self, user_id):
        """
        Fetches the user's account ID and role from the database.

        Args:
            user_id (int): The ID of the user to fetch.

        Returns:
            tuple: A tuple containing the user's account ID and role.

        Raises:
            CustomUser.DoesNotExist: If the user does not exist.
        """
        user = CustomUser.objects.values('account_id', 'role').get(pk=user_id)
        return (user['account_id'], user['role'])

    async def __call__(self, scope, receive, send):
        """
        Handles the WebSocket connection, authenticating the user via JWT token.

        Args:
            scope (dict): The connection scope.
            receive (callable): The receive function to get messages from the client.
            send (callable): The send function to send messages to the client.
        """
        headers = dict(scope['headers'])

        # Check if the 'cookie' header is present
        if b'cookie' in headers:
            try:
                # Decode the cookies
                cookies = headers[b'cookie'].decode()
                cookie_dict = {}
                for cookie in cookies.split('; '):
                    cookie_parts = cookie.split('=')
                    cookie_dict[cookie_parts[0]] = cookie_parts[1] if len(cookie_parts) > 1 else ''

                # Retrieve the access token from the cookies
                access_token = cookie_dict.get('access_token')

                # Check if the access token is in cache (indicating it might be invalid)
                if not access_token or cache.get(access_token):
                    return await send({'type': 'websocket.close', 'code': 1000, 'error': 'Request not authenticated.. access denied'})

                # Validate the access token
                authorized = validate_access_token(access_token)

                # If the token is not valid, close the connection
                if authorized is None:
                    return await send({'type': 'websocket.close', 'code': 1000, 'error': 'Invalid security credentials.. request revoked'})

                # Decode the access token to get the user ID
                decoded_token = AccessToken(access_token)

                # Fetch the user and their role from the database
                scope['user'], scope['role'] = await self.get_user(decoded_token['user_id'])
                scope['access_token'] = access_token

            except ObjectDoesNotExist:
                # If the user does not exist, close the connection
                return await send({'type': 'websocket.close', 'code': 1000, 'error': 'Invalid credentials.. no such user exists'})

            # If any other exception occurs, close the connection and send the error message
            except Exception as e:
                return await send({'type': 'websocket.close', 'code': 1000, 'error': str(e)})

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

        Raises:
            ConnectionError: If the user already has 3 or more active connections.
        """
        if account_id not in self.active_connections:
            self.active_connections[account_id] = []

        # Check if the user already has 3 or more connections
        if len(self.active_connections[account_id]) >= 3:
            await websocket.send(text_data=json.dumps({'error': 'Too many connections. Limit is 3, disconnect one of your other devices to connect this one'}))
            await websocket.close()
            return

        self.active_connections[account_id].append(websocket)

    async def disconnect(self, account_id, websocket):
        """
        Removes a WebSocket connection for a user.

        Args:
            account_id (str): The account ID of the user.
            websocket (WebSocket): The WebSocket connection instance.
        """
        if account_id in self.active_connections:
            self.active_connections[account_id].remove(websocket)
            if not self.active_connections[account_id]:
                del self.active_connections[account_id]

    async def send_message(self, account_id, message):
        """
        Sends a message to all active WebSocket connections for a user.

        Args:
            account_id (str): The account ID of the user.
            message (dict): The message to send.
        """
        if account_id in self.active_connections:
            for connection in self.active_connections[account_id]:
                await connection.send(text_data=json.dumps(message))

    def get_active_connections(self):
        """
        Returns the current active connections.

        Returns:
            dict: A dictionary of active connections.
        """
        return self.active_connections

# Initialize the ConnectionManager instance
connection_manager = ConnectionManager()
