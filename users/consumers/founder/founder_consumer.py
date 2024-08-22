# python 
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# websocket manager
from seeran_backend.middleware import  connection_manager

# utility functions
from authentication.utils import validate_access_token

# async functions 
from users.consumers.general import general_search_async_functions
from . import founder_async_functions


class FounderConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role != 'FOUNDER':
            return await self.close()
                        
        account_id = self.scope['user']
        await connection_manager.connect(account_id, self)

        await self.accept()
        return await self.send(text_data=json.dumps({'message': 'Welcome Back'}))

    async def disconnect(self, close_code):
        account_id = self.scope['user']
        await connection_manager.disconnect(account_id, self)

    async def receive(self, text_data):
        user = self.scope.get('user')
        access_token = self.scope.get('access_token')

        if not (user and access_token and validate_access_token(access_token)):
            await self.send(text_data=json.dumps({'error': 'request not authenticated.. access denied'}))
            return await self.close()

        data = json.loads(text_data)
        action = data.get('action')
        description = data.get('description')
        details = data.get('details')

        if not action or not description:
            return await self.send(text_data=json.dumps({'error': 'invalid request..'}))

        response = await self.handle_request(action, description, details, user, access_token)
        
        if response is not None:
            return await self.send(text_data=json.dumps(response))
        
        return await self.send(text_data=json.dumps({'error': 'provided information is invalid.. request revoked'}))

    async def handle_request(self, action, description, details, user, access_token): # re Handle 
        action_map = {
            'GET': self.handle_get,
            'SEARCH': self.handle_search,
            'VERIFY': self.handle_verify,
            'PUT': self.handle_put,
            'POST': self.handle_post,
        }

        handler = action_map.get(action)
        if handler:
            return await handler(description, details, user, access_token)
        
        return {'error': 'Invalid action'}

    async def handle_get(self, description, details, user, access_token):
        if description == 'my_security_information':
            return await general_search_async_functions.fetch_my_security_information(user)
        
        elif description == 'schools':
            return await founder_async_functions.fetch_schools()
        
        elif description == 'log_out':
            return await general_search_async_functions.log_out(access_token)
        
        else:
            return {'error': 'Invalid get description'}
        
    async def handle_search(self, description, details, user, access_token):
        search_map = {
            'school': founder_async_functions.search_school,
            'school_details': founder_async_functions.search_school_details,

            'principal_profile': founder_async_functions.search_principal_profile,
            'principal_id': founder_async_functions.search_principal_id,

            'principal_invoices': founder_async_functions.search_principal_invoices,
            'principal_invoice': founder_async_functions.search_principal_invoice,

            'bug_reports': founder_async_functions.search_bug_reports,
            'bug_report': founder_async_functions.search_bug_report,
        }

        func = search_map.get(description)
        if func:
            return await func(details)
        
        return {'error': 'Invalid search description'}

    async def handle_verify(self, description, details, user, access_token):

        if description == 'verify_email':
            response = await general_search_async_functions.verify_email(details)
            if response.get('user'):
                return await general_search_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your email update request..')
            
        elif description == 'verify_password':
            response = await general_search_async_functions.verify_password(user, details)
            if response.get('user'):
                return await general_search_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your password update request..')
            
        elif description == 'verify_otp':
            return await general_search_async_functions.verify_otp(user, details)
        
        else:
            return {'error': 'Invalid verify description'}

    async def handle_put(self, description, details, user, access_token):

        if description == 'update_email':
            return await general_search_async_functions.update_email(user, details, access_token)
        
        elif description == 'update_password':
            return await general_search_async_functions.update_password(user, details, access_token)
        
        elif description == 'update_multi_factor_authentication':
            return await general_search_async_functions.update_multi_factor_authentication(user, details)
        
        elif description == 'update_bug_report':
            return await founder_async_functions.update_bug_report(details)
        
        elif description == 'update_account':
            return await founder_async_functions.update_principal_account(details)
        
        else:
            return {'error': 'Invalid put description'}

    async def handle_post(self, description, details, user, access_token):

        if description == 'create_school_account':
            return await founder_async_functions.create_school_account(details)
        
        elif description == 'delete_school_account':
            return await founder_async_functions.delete_school_account(details)
        
        elif description == 'create_principal_account':
            response = await founder_async_functions.create_principal_account(details)
            if response.get('user'):
                return await general_search_async_functions.send_account_confirmation_email(response.get('user'))
            return response
            
        elif description == 'delete_principal_account':
            return await founder_async_functions.delete_principal_account(details)
        
        else:
            return {'error': 'Invalid post description'}
