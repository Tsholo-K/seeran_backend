from channels.generic.websocket import AsyncWebsocketConsumer
import json

# django
from django.db.models import Count, Q
from django.db import models

from users.models import CustomUser
from schools.models import School

# serializers
from schools.serializers import SchoolCreationSerializer, SchoolsSerializer, SchoolSerializer, SchoolDetailsSerializer

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
                    response = await self.fetch_security_info(user)
                
                # return all school objects
                if description == 'schools':
                    response = await self.fetch_schools()
                    
                return await self.send(text_data=json.dumps(response))
            
            details = json.loads(text_data).get('details')
            
            if not details:
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. permission denied' }))

            if action == 'SEARCH':
                
                # return school with the provided id
                if description == 'school':
                    school_id = details.get('school_id')
                    if school_id is not None:
                        response = await self.fetch_school(school_id)
                        
                # return school details for school with the provided id
                if description == 'school_details':
                    school_id = details.get('school_id')
                    if school_id is not None:
                        response = await self.fetch_school_details(school_id)
            
            if action == 'PUT':
                
                # toggle  multi-factor authentication option for user
                if description == 'multi_factor_authentication':
                    toggle = details.get('toggle')
                    if toggle is not None:
                        response = await self.toggle_multi_factor_authentication(user, toggle)
                    
            if response !=  None:
                return await self.send(text_data=json.dumps(response))
            
            return await self.send(text_data=json.dumps({ 'error': 'provided information is invalid.. request revoked' }))

        return await self.send(text_data=json.dumps({ 'error': 'request not authenticated.. access denied' }))

      
    @sync_to_async
    def fetch_security_info(self, user):

        try:
            user = CustomUser.objects.get(account_id=user)
            return { 'multifactor_authentication': user.multifactor_authentication, 'event_emails': user.event_emails }
            
        except CustomUser.DoesNotExist:
            return { 'error': 'user with the provided credentials does not exist' }
        
        except Exception as e:
            return { 'error': str(e) }

    @sync_to_async
    def toggle_multi_factor_authentication(self, user, toggle):
        # Example: Fetch security information asynchronously from CustomUser model
        try:
            user = CustomUser.objects.get(account_id=user)
            user.multifactor_authentication = toggle
            user.save()
            
            return {'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}
        
        except CustomUser.DoesNotExist:
            return { 'error': 'user with the provided credentials does not exist' }
        
        except Exception as e:
            return { 'error': str(e) }

    @sync_to_async
    def fetch_schools(self):

        try:
            schools = School.objects.all().annotate(
                students=Count('users', filter=models.Q(users__role='STUDENT')),
                parents=Count('users', filter=models.Q(users__role='PARENT')),
                teachers=Count('users', filter=models.Q(users__role='TEACHER'))
            )
            
            serializer = SchoolsSerializer(schools, many=True)
            return { 'schools' : serializer.data }
        
        except Exception as e:
            return { 'error': str(e) }
        
    @sync_to_async
    def fetch_school(self, school_id):
        
        try:
            school = School.objects.get(school_id=school_id)
            serializer = SchoolSerializer(instance=school)
        
            return {"school" : serializer.data}
        
        except School.DoesNotExist:
            return {"error" : "school with the provided credentials can not be found"}
        
        except Exception as e:
            return {"error" : str(e)}
        
    @sync_to_async
    def fetch_school_details(self, school_id):
        
        try:
            school = School.objects.filter(school_id=school_id).annotate(
                students=Count('users', filter=Q(users__role='STUDENT')),
                parents=Count('users', filter=Q(users__role='PARENT')),
                teachers=Count('users', filter=Q(users__role='TEACHER')),
                admins=Count('users', filter=Q(users__role='ADMIN') | Q(users__role='PRINCIPAL')),
            )
            serializer = SchoolDetailsSerializer(instance=school)
        
            return {"school" : serializer.data}
        
        except School.DoesNotExist:
            return {"error" : "school with the provided credentials can not be found"}
        
        except Exception as e:
            return {"error" : str(e)}
