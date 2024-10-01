# python 
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# websocket manager
from seeran_backend.middleware import  connection_manager

# utility functions
from authentication.utils import validate_access_token

# founder async functions 
from . import founder_connect_async_functions
from . import founder_create_async_functions
from . import founder_delete_async_functions
from . import founder_search_async_functions
from . import founder_update_async_functions
from . import founder_view_async_functions

# general async functions 
from websockets.consumers.general import general_submit_async_functions
from websockets.consumers.general import general_update_async_functions
from websockets.consumers.general import general_view_async_functions
from websockets.consumers.general import general_verify_async_functions
from websockets.consumers.general import general_email_async_functions


class FounderConsumer(AsyncWebsocketConsumer):

# CONNECT

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope['role']
        if role != 'FOUNDER':
            return await self.close()
        
        await self.accept()
                        
        account = self.scope['account']
        await connection_manager.connect(account, self)

        response = await founder_connect_async_functions.account_details(account, role)
        if 'error' in response:
            await self.send(text_data=json.dumps(response))
            await connection_manager.disconnect(account, self)
            return await self.close()

# DISCONNECT

    async def disconnect(self, close_code):
        account_id = self.scope.get('user')
        if account_id:
            await connection_manager.disconnect(account_id, self)

# RECIEVE

    async def receive(self, text_data):
        user = self.scope.get('user')
        role = self.scope.get('role')
        access_token = self.scope.get('access_token')

        if not (user and role and access_token and validate_access_token(access_token)):
            await self.send(text_data=json.dumps({'error': 'request not authenticated.. access denied'}))
            return await self.close()

        data = json.loads(text_data)
        action = data.get('action')
        description = data.get('description')
        details = data.get('details')

        if not action or not description:
            return await self.send(text_data=json.dumps({'error': 'invalid request..'}))

        response = await self.handle_request(action, description, details, user, role, access_token)
        
        if response is not None:
            return await self.send(text_data=json.dumps(response))
        
        return await self.send(text_data=json.dumps({'error': 'provided information is invalid.. request revoked'}))

# HANDLER/ROUTER

    async def handle_request(self, action, description, details, user, role, access_token):
        action_map = {
            'VIEW': self.handle_view,
            'SEARCH': self.handle_search,
            'VERIFY': self.handle_verify,
            'UPDATE': self.handle_update,
            'SUBMIT': self.handle_submit,
            'DELETE': self.handle_delete,
            'CREATE': self.handle_create,
        }

        handler = action_map.get(action)
        if handler:
            return await handler(description, details, user, role, access_token)
        
        return {'error': 'Could not process your request, an invalid action was provided. If this problem persist open a bug report ticket.'}

# VIEW

    async def handle_view(self, description, details, user, role, access_token):
        if description == 'view_my_security_information':
            return await general_view_async_functions.view_my_security_information(user, role)
        
        elif description == 'view_schools':
            return await founder_view_async_functions.view_schools()
        
        return {'error': 'Could not process your request, an invalid view description was provided. If this problem persist open a bug report ticket.'}
        
# SEARCH

    async def handle_search(self, description, details, user, role, access_token):
        search_map = {
            'school': founder_search_async_functions.search_school,
            'school_details': founder_search_async_functions.search_school_details,

            'principal_profile': founder_search_async_functions.search_principal_profile,
            'principal_details': founder_search_async_functions.search_principal_details,

            'principal_invoices': founder_search_async_functions.search_principal_invoices,
            'principal_invoice': founder_search_async_functions.search_principal_invoice,

            'bug_reports': founder_search_async_functions.search_bug_reports,
            'bug_report': founder_search_async_functions.search_bug_report,
        }

        func = search_map.get(description)
        if func:
            return await func(details)
        
        return {'error': 'Could not process your request, an invalid search description was provided. If this problem persist open a bug report ticket.'}

# VERIFY

    async def handle_verify(self, description, details, user, role, access_token):

        if description == 'verify_email_address':
            response = await general_verify_async_functions.verify_email_address(details)
            if response.get('user'):
                return await general_email_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your email update request..')
            return response
        
        elif description == 'verify_password':
            response = await general_verify_async_functions.verify_password(user, details)
            if response.get('user'):
                return await general_email_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your password update request..')
            return response
        
        elif description == 'verify_otp':
            return await general_verify_async_functions.verify_otp(user, details)
        
        return {'error': 'Could not process your request, an invalid verify description was provided. If this problem persist open a bug report ticket.'}

# UPDATE

    async def handle_update(self, description, details, user, role, access_token):

        if description == 'update_email_address':
            return await general_update_async_functions.update_email_address(user, details, access_token)
        
        elif description == 'update_password':
            return await general_update_async_functions.update_password(user, details, access_token)
        
        elif description == 'update_multi_factor_authentication':
            return await general_update_async_functions.update_multi_factor_authentication(user, details)

        elif description == 'update_bug_report_details':
            return await founder_update_async_functions.update_bug_report_details(details)
        
        elif description == 'update_principal_account_details':
            return await founder_update_async_functions.update_principal_account_details(details)
                
        elif description == 'update_school_details_details':
            return await founder_update_async_functions.update_school_account_details(details)
        
        return {'error': 'Could not process your request, an invalid update description was provided. If this problem persist open a bug report ticket.'}

# SUBMIT

    async def handle_submit(self, description, details, user, role, access_token):
        if description == 'submit_log_out_request':
            return await general_submit_async_functions.submit_log_out_request(access_token)
        
        return {'error': 'Could not process your request, an invalid submit description was provided. If this problem persist open a bug report ticket.'}

# DELETE

    async def handle_delete(self, description, details, user, role, access_token):
        if description == 'delete_school_account':
            return await founder_delete_async_functions.delete_school_account(details)
            
        elif description == 'delete_principal_account':
            return await founder_delete_async_functions.delete_principal_account(details)
        
        return {'error': 'Could not process your request, an invalid delete description was provided. If this problem persist open a bug report ticket.'}

# CREATE

    async def handle_create(self, description, details, user, role, access_token):
        if description == 'create_school_account':
            return await founder_create_async_functions.create_school_account(details)
        
        elif description == 'create_principal_account':
            response = await founder_create_async_functions.create_principal_account(details)
            if response.get('user'):
                return await general_email_async_functions.send_account_confirmation_email(response.get('user'))
            return response
        
        return {'error': 'Could not process your request, an invalid create description was provided. If this problem persist open a bug report ticket.'}
