from channels.generic.websocket import AsyncWebsocketConsumer
import json

from users.models import CustomUser
from users.serializers import SecurityInfoSerializer
from asgiref.sync import sync_to_async  # Import sync_to_async for database_sync_to_async

class MainConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'message': 'WebSocket connection established'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        
        user = self.scope.get('user')
        
        if user:
            action = json.loads(text_data).get('action')
            description = json.loads(text_data).get('description')
            
            
            if not ( action or description ):
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. permission denied' }))

            if action == 'GET':
                
                # return users security information
                if description == 'my_security_information':
                    security_info = await self.fetch_security_info(user)
                    
                    if security_info is not None:
                        serializer = SecurityInfoSerializer(data=security_info)  # Serialize fetched data
                        
                        if serializer.is_valid():  # Validate serialized data
                            return await self.send(text_data=json.dumps({'user_data': serializer.data }))
                        
                        return await self.send(text_data=json.dumps({ 'error': 'failed to serialize data' }))
                        
                    return await self.send(text_data=json.dumps({ 'error': 'user with the provided credentials does not exist' }))
            
            details = json.loads(text_data).get('details')
            
            if not details:
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. permission denied' }))

            if action == 'PUT':
                
                # toggle  multi-factor authentication option for user
                if description == 'multi_factor_authentication':
                    message = await self.toggle_multi_factor_authentication(user, details.toggle)
                    
                    if message is not None:
                        return await self.send(text_data=json.dumps({ 'message': message }))
                        
                    return await self.send(text_data=json.dumps({ 'error': 'user with the provided credentials does not exist' }))
                
        return await self.send(text_data=json.dumps({ 'error': 'request not authenticated.. access denied' }))


    @sync_to_async
    def toggle_multi_factor_authentication(self, user, toggle):
        # Example: Fetch security information asynchronously from CustomUser model
        try:
            user = CustomUser.objects.get(id=user.id)
            user.multifactor_authentication = toggle
            user.save()
            
            return {'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}
        
        except CustomUser.DoesNotExist:
            return None
      
        
    @sync_to_async
    def fetch_security_info(self, user):
        # Example: Fetch security information asynchronously from CustomUser model
        try:
            user = CustomUser.objects.get(id=user.id)
            return {
                'multifactor_authentication': user.multifactor_authentication,
                'event_emails': user.event_emails,
                # Add more fields as needed
            }
            
        except CustomUser.DoesNotExist:
            return None