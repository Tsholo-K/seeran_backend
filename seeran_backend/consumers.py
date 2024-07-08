from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from users.models import CustomUser
from users.serializers import SecurityInfoSerializer
from asgiref.sync import sync_to_async  # Import sync_to_async for database_sync_to_async

class MainConsumer(AsyncWebsocketConsumer):
    
    @database_sync_to_async
    def fetch_security_info(self, user_id):
        return CustomUser.objects.get(pk=user_id)


    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'message': 'WebSocket connection established'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'my_security_information':
            # Example: Fetch security information based on user context
            user = self.scope.get('user')
            
            if user:
                security_info = await self.fetch_security_info(user)
                if security_info is not None:
                    serializer = SecurityInfoSerializer(data=security_info)  # Serialize fetched data
                    if serializer.is_valid():  # Validate serialized data
                        await self.send(text_data=json.dumps({ 'action': 'your_security_information', 'data': serializer.data }))
                    else:
                        await self.send(text_data=json.dumps({ 'error': 'failed to serialize data' }))
                
            await self.send(text_data=json.dumps({ 'error': 'request not authenticated.. access denied' }))

    @sync_to_async
    def fetch_security_info(self, user):
        # Example: Fetch security information asynchronously from CustomUser model
        # Replace with your actual data fetching logic
        try:
            user = CustomUser.objects.get(id=user.id)
            
            return {
                'multifactor_authentication': user.multifactor_authentication,
                'event_emails': user.event_emails,
                # Add more fields as needed
            }
            
        except CustomUser.DoesNotExist:
            return None