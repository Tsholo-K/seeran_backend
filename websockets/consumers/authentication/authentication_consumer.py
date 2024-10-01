# python 
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# consumers
from websockets.consumers.founder.founder_consumer import FounderConsumer
from websockets.consumers.admin.admin_consumer import AdminConsumer
from websockets.consumers.teacher.teacher_consumer import TeacherConsumer
from websockets.consumers.parent.parent_consumer import ParentConsumer
from websockets.consumers.student.student_consumer import StudentConsumer


class AccountsWebsocketHandler(AsyncWebsocketConsumer):

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
        
        role_specific_consumer_mapping = {
            'FOUNDER': FounderConsumer.as_asgi(),
            'PRINCIPAL': AdminConsumer.as_asgi(),
            'ADMIN': AdminConsumer.as_asgi(),
            'TEACHER': TeacherConsumer.as_asgi(),
            'STUDENT': StudentConsumer.as_asgi(),
            'PARENT': ParentConsumer.as_asgi(),
        }
        
        print(f"Role: {self.role}")
        print(f"Scope: {self.scope}")
        print(f"Receive: {self.receive}")
        print(f"Send: {self.send}")

        consumer_class = role_specific_consumer_mapping.get(self.role)

        if consumer_class:
            try:
                # Check if the scope, receive, and send are None
                if self.scope is None:
                    raise ValueError("self.scope is None")
                if self.receive is None:
                    raise ValueError("self.receive is None")
                if self.send is None:
                    raise ValueError("self.send is None")

                await consumer_class(self.scope, self.receive, self.send)
            except TypeError as te:
                print(f"Type error in WebsocketHandler delegation: {str(te)}")
                await self.close()
            except AttributeError as ae:
                print(f"Attribute error in WebsocketHandler delegation: {str(ae)}")
                await self.close()
            except ValueError as ve:
                print(f"Value error in WebsocketHandler delegation: {str(ve)}")
                await self.close()
            except Exception as e:
                print(f"General error in WebsocketHandler delegation: {str(e)}")
                await self.close()
        else:
            print("Unknown role, closing connection.")
            await self.close()

    async def return_error_message_and_close_connection(self, description,  message):
        """Return an error message to the frontend and close connection."""
        # Accept the connection so we can send the error message
        await self.accept()

        # Send the error message
        await self.send(text_data=json.dumps({description: message}))

        # Close the connection after sending the error
        return await self.close()

