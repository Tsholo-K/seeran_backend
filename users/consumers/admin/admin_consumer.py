from channels.generic.websocket import AsyncWebsocketConsumer
import json

from channels.db import database_sync_to_async

from users.models import CustomUser

class AdminConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role not in ['ADMIN', 'PRINCIPAL']:
            return await self.close()
        
        await self.accept()
        return await self.send(text_data=json.dumps({ 'message': 'WebSocket connection established' }))


    async def disconnect(self, close_code):
        pass


    async def receive(self, text_data):
        
        user = self.scope.get('user')
        
        if user:
            response = None

            action = json.loads(text_data).get('action')
            description = json.loads(text_data).get('description')
            
            if not ( action or description ):
                return await self.send(text_data=json.dumps({ 'error': 'invalid request..' }))


            ################################################ GET #######################################################


            if action == 'GET':
                
                # return users security information
                if description == 'my_security_information':
                    response = await self.fetch_security_info(user)


            ##############################################################################################################


                if response is not None:
                    return await self.send(text_data=json.dumps(response))
                
                return await self.send(text_data=json.dumps({ 'error': 'provided information is invalid.. request revoked' }))
            
            details = json.loads(text_data).get('details')
            
            if not details:
                return await self.send(text_data=json.dumps({ 'error': 'invalid request.. request denied' }))


            ############################################## SEARCH ########################################################


            if action == 'SEARCH':
                ...


            ##############################################################################################################

            ################################################ PUT ##########################################################


            if action == 'PUT':
                
                # toggle  multi-factor authentication option for user
                if description == 'multi_factor_authentication':
                    toggle = details.get('toggle')
                    if toggle is not None:
                        response = await self.update_multi_factor_authentication(user, toggle)


            ################################################################################################################                
                        
            ################################################# POST ##########################################################


            if action == 'POST':
                ...
                

            ###############################################################################################################
        
                        
            if response is not None:
                return await self.send(text_data=json.dumps(response))
            
            
            return await self.send(text_data=json.dumps({ 'error': 'provided information is invalid.. request revoked' }))
        
        return await self.send(text_data=json.dumps({ 'error': 'request not authenticated.. access denied' }))


########################################################## Aysnc Functions ########################################################


    @database_sync_to_async
    def fetch_security_info(self, user):

        try:
            user = CustomUser.objects.get(account_id=user)
            return { 'multifactor_authentication': user.multifactor_authentication, 'event_emails': user.event_emails }
            
        except CustomUser.DoesNotExist:
            return { 'error': 'user with the provided credentials does not exist' }
        
        except Exception as e:
            return { 'error': str(e) }
        

    @database_sync_to_async
    def update_multi_factor_authentication(self, user, toggle):

        try:
            user = CustomUser.objects.get(account_id=user)
            user.multifactor_authentication = toggle
            user.save()
            
            return {'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}
        
        except CustomUser.DoesNotExist:
            return { 'error': 'user with the provided credentials does not exist' }
        
        except Exception as e:
            return { 'error': str(e) }
