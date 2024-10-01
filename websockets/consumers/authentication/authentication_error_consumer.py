# python 
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer


class UnathenticationError(AsyncWebsocketConsumer):
        
# CONNECT

    async def connect(self):
        # Check if authentication failed in the middleware
        authentication_error = self.scope.get('authentication_error')

        if authentication_error:
            return await self.return_error_message_and_close_connection('websocket_unauthenticated',  authentication_error)

        self.role = self.scope.get('role')
        self.account = self.scope.get('account')
        self.access_token = self.scope.get('access_token')

        if not self.role:
            return await self.return_error_message_and_close_connection(
                'websocket_error',
                'Authentication failed, your account role is missing. Please log in again to obtain the correct permissions.'
            )

        elif not self.account:
            return await self.return_error_message_and_close_connection(
                'websocket_error',
                'Authentication failed, your account information is missing. Please ensure you are logged in and try reconnecting.'
            )

        elif not self.access_token:
            return await self.return_error_message_and_close_connection(
                'websocket_error',
                'Authentication failed, your access token is missing. Please log in again to obtain the correct permissions.'
            )

    async def return_error_message_and_close_connection(self, description,  message):
        """Return an error message to the frontend and close connection."""
        # Accept the connection so we can send the error message
        await self.accept()

        # Send the error message
        await self.send(text_data=json.dumps({description: message}))

        # Close the connection after sending the error
        return await self.close()

