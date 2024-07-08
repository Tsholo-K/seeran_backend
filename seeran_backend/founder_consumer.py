from channels.generic.websocket import AsyncWebsocketConsumer
import json

# django
from django.db.models import Count
from django.db import models
from django.forms.models import model_to_dict

from users.models import CustomUser
from schools.models import School

# serializers
from schools.serializers import SchoolCreationSerializer, SchoolsSerializer, SchoolSerializer, SchoolDetailsSerializer
from users.serializers import SecurityInfoSerializer

from asgiref.sync import sync_to_async  # Import sync_to_async for database_sync_to_async


class FounderConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role != 'FOUNDER':
            # Optionally, send a message to the client before closing the connection
            await self.send(text_data=json.dumps({ 'error': 'insufficient permissions' }))
            return await self.close()
        
        await self.accept()
        return await self.send(text_data=json.dumps({ 'message': 'WebSocket connection established' }))


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
                            return await self.send(text_data=json.dumps( serializer.data ))
                        
                        return await self.send(text_data=json.dumps({ 'error': serializer.errors }))
                        
                    return await self.send(text_data=json.dumps({ 'error': 'user with the provided credentials does not exist' }))
                
                # return all school objects
                if description == 'schools':
                    schools = await self.fetch_schools()
                    
                    serializer = SchoolsSerializer(data=schools, many=True)  # Serialize fetched data

                    if serializer.is_valid():  # Validate serialized data
                        return await self.send(text_data=json.dumps({ 'schools' : serializer.data }))
                        
                    return await self.send(text_data=json.dumps({ 'error': serializer.errors }))
            
            details = json.loads(text_data).get('details')
            
            if not details:
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. permission denied' }))

            if action == 'PUT':
                
                # toggle  multi-factor authentication option for user
                if description == 'multi_factor_authentication':
                    toggle = details.get('toggle')
                    
                    if toggle is not None:
                        response = await self.toggle_multi_factor_authentication(user, toggle)
                                            
                        if response is not None:
                            return await self.send(text_data=json.dumps( response ))
                            
                        return await self.send(text_data=json.dumps({ 'error': 'user with the provided credentials does not exist' }))
                    
                    return await self.send(text_data=json.dumps({ 'error': 'invalid information.. provided information is invalid' }))
                
        return await self.send(text_data=json.dumps({ 'error': 'request not authenticated.. access denied' }))

      
    @sync_to_async
    def fetch_security_info(self, user):

        try:
            user = CustomUser.objects.get(account_id=user)
            return { 'multifactor_authentication': user.multifactor_authentication, 'event_emails': user.event_emails }
            
        except CustomUser.DoesNotExist:
            return None
        
    @sync_to_async
    def toggle_multi_factor_authentication(self, user, toggle):
        # Example: Fetch security information asynchronously from CustomUser model
        try:
            user = CustomUser.objects.get(account_id=user)
            user.multifactor_authentication = toggle
            user.save()
            
            return {'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}
        
        except CustomUser.DoesNotExist:
            return None
        
    @sync_to_async
    def fetch_schools(self):

        try:
            schools = School.objects.all().annotate(
                students=Count('users', filter=models.Q(users__role='STUDENT')),
                parents=Count('users', filter=models.Q(users__role='PARENT')),
                teachers=Count('users', filter=models.Q(users__role='TEACHER'))
            )
            # Convert each School instance to a dictionary
            school_dicts = [model_to_dict(school) for school in schools]
            return school_dicts
        
        # if any exception occurs during the proccess return an error
        except Exception as e:
            return { 'error': str(e) }
