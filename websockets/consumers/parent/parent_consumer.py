# python
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# websocket manager
from seeran_backend.middleware import connection_manager

# utility functions
from authentication.utils import validate_access_token

# admin async functions 
from . import parent_connect_async_functions
from . import parent_view_async_functions
from . import parent_search_async_functions

# general async functions
from websockets.consumers.general import general_message_async_functions
from websockets.consumers.general import general_submit_async_functions
from websockets.consumers.general import general_update_async_functions
from websockets.consumers.general import general_search_async_functions
from websockets.consumers.general import general_view_async_functions
from websockets.consumers.general import general_verify_async_functions
from websockets.consumers.general import general_email_async_functions


class ParentConsumer(AsyncWebsocketConsumer):

# CONNECT

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope['role']

        # Check if the user has the required role
        if role not in ['PARENT']:
            return await self.close()

        account = self.scope['account']

        await self.accept()

        response = await parent_connect_async_functions.account_details(account, role)
        if 'error' in response or 'denied' in response:
            await self.send(text_data=json.dumps(response))
            return await self.close()

        await connection_manager.connect(account, self)
        await self.send(text_data=json.dumps(response))

# DISCONNECT

    async def disconnect(self, close_code):
        account = self.scope['account']
        if account:
            await connection_manager.disconnect(account, self)

# RECIEVE

    async def receive(self, text_data):
        account = self.scope.get('account')
        role = self.scope.get('role')
        access_token = self.scope.get('access_token')

        if not (account and role and access_token and validate_access_token(access_token)):
            await self.send(text_data=json.dumps({'error': 'request not authenticated.. access denied'}))
            return await self.close()

        data = json.loads(text_data)
        action = data.get('action')
        description = data.get('description')
        details = data.get('details')

        if not action or not description:
            return await self.send(text_data=json.dumps({'error': 'invalid request..'}))

        response = await self.handle_request(action, description, details, account, role, access_token)
        
        if response:
            return await self.send(text_data=json.dumps(response))
        
        return await self.send(text_data=json.dumps({'error': 'provided information is invalid.. request revoked'}))

# HANDLER/ROUTER

    async def handle_request(self, action, description, details, account, role, access_token):
        action_map = {
            'VIEW': self.handle_view,
            'SEARCH': self.handle_search,
            'VERIFY': self.handle_verify,
            'FORM DATA': self.handle_form_data,
            'UPDATE': self.handle_update,
            'MESSAGE': self.handle_message,
            'SUBMIT': self.handle_submit,
            'DELETE': self.handle_delete,
            'CREATE': self.handle_create,
        }

        handler = action_map.get(action)
        if handler:
            return await handler(description, details, account, role, access_token)
        
        return {'error': 'Could not process your request, an invalid action was provided. If this problem persist open a bug report ticket.'}

# VIEW

    async def handle_view(self, description, details, account, role, access_token):
        view_map = {
            'view_my_security_information': general_view_async_functions.view_my_security_information,
            'view_my_email_address_status_information': general_view_async_functions.view_my_email_address_status_information,

            'view_chat_rooms': general_view_async_functions.view_chat_rooms,

            'view_school_announcements': parent_view_async_functions.view_school_announcements,

            'children': parent_view_async_functions.children,
        }

        func = view_map.get(description)
        if func:
            if description in ['view_chat_rooms', 'view_my_email_address_status_information']:
                return await func(account)
            else:
                return await func(account, role)

        return {'error': 'Could not process your request, an invalid view description was provided. If this problem persist open a bug report ticket.'}

# SEARCH

    async def handle_search(self, description, details, account, role, access_token):
        search_map = {
            'search_email_ban': general_search_async_functions.search_email_ban,

            'search_chat_room': general_search_async_functions.search_chat_room,
            'search_chat_room_messages': general_search_async_functions.search_chat_room_messages,

            'search_grade_terms': parent_search_async_functions.search_grade_terms,

            'search_classroom': parent_search_async_functions.search_classroom,
            
            'search_student_classrooms': parent_search_async_functions.search_student_classrooms,
            'search_student_classroom_performance': parent_search_async_functions.search_student_classroom_performance,

            'search_student_attendance': parent_search_async_functions.search_student_attendance,

            'search_student_classroom_card': parent_search_async_functions.search_student_classroom_card,
            'search_student_activity': parent_search_async_functions.search_student_activity,

            'search_student_assessment_transcript': parent_search_async_functions.search_student_assessment_transcript,

            'search_group_timetables': parent_search_async_functions.search_group_timetables,
            'search_group_timetable_timetables': parent_search_async_functions.search_group_timetable_timetables,

            'search_timetable_sessions': parent_search_async_functions.search_timetable_sessions,
        }

        func = search_map.get(description)
        
        if func:
            if description in ['search_email_ban']:
                response = await func(details) 
            elif description in ['search_chat_room_messages']:
                response = await func(account, details)
            elif description in ['search_student_attendance', 'search_group_timetables']:
                response = await func(account, role)
            else:
                response =  await func(account, role, details)

            if description in ['search_chat_room_messages'] and response.get('user'):
                await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                await connection_manager.send_message(account, json.dumps({'unread_messages': response['unread_messages']}))

                return {'messages': response['messages'], 'next_cursor': response['next_cursor']}  

            return response

        return {'error': 'Could not process your request, an invalid search description was provided. If this problem persist open a bug report ticket.'}

# VERIFY

    async def handle_verify(self, description, details, account, role, access_token):
        verify_map = {
            'verify_email': general_verify_async_functions.verify_email_address,
            'verify_password': general_verify_async_functions.verify_password,

            'verify_otp': general_verify_async_functions.verify_otp,

            'verify_email_ban_revalidation_otp_send': general_verify_async_functions.verify_email_ban_revalidation_otp_send,
            'verify_email_ban_revalidation_otp': general_verify_async_functions.verify_email_ban_revalidation_otp,
        }

        func = verify_map.get(description)
        if func:
            if description in ['verify_email']:
                response = await func(role, details)
            else:
                response = await func(account, details)

            if response.get('user'):
                if description in ['verify_email', 'verify_password']:
                    return await general_email_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your request.')
                elif description in ['verify_email_ban_revalidation_otp_send']:
                    response = await general_email_async_functions.send_email_revalidation_one_time_pin_email(response['user'])

                    if response.get('message'):
                        return await general_update_async_functions.update_email_ban_otp_sends(details)

            return response

        return {'error': 'Could not process your request, an invalid verify description was provided. If this problem persist open a bug report ticket.'}

# FORM DATA

    async def handle_form_data(self, description, details, account, role, access_token):
        return {'error': 'Could not process your request, an invalid form data description was provided. If this problem persist open a bug report ticket.'}
        form_data_map = {}

        func = form_data_map.get(description)
        if func:
            response = await func(account, role, details)
            return response
        

# UPDATE

    async def handle_update(self, description, details, account, role, access_token):
        update_map = {
            'update_email_address': general_update_async_functions.update_email_address,
            'update_password': general_update_async_functions.update_password,

            'update_multi_factor_authentication': general_update_async_functions.update_multi_factor_authentication,
            
            'update_messages_as_read': general_update_async_functions.update_messages_as_read,
        }

        func = update_map.get(description)
        if func:
            if description in ['update_email_address', 'update_password']:
                response = await func(account, role, details, access_token)
            elif description in ['update_multi_factor_authentication', 'update_messages_as_read']:
                response = await func(account, details)
            else:
                response = await func(account, role, details)

            if response.get('user'):
                if description in ['update_messages_as_read']:
                    await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                    return {'message': 'read receipt sent'}
                
            return response
        
        return {'error': 'Could not process your request, an invalid update description was provided. If this problem persist open a bug report ticket.'}

# MESSAGE

    async def handle_message(self, description, details, account, role, access_token):
        message_map = {
            'message_private': general_message_async_functions.message_private,
        }

        func = message_map.get(description)
        if func:
            response = await func(account, role, details)
            if response.get('reciever'):
                await connection_manager.send_message(response['recipient']['account_id'], json.dumps({'description': 'text_message', 'message': response['message'], 'author': response['author']}))
                await connection_manager.send_message(response['author']['account_id'], json.dumps({'description': 'text_message_fan', 'message': response['message'], 'recipient': response['recipient']}))

                return {'message': 'private message successfully sent'}
            
        return {'error': 'Could not process your request, an invalid text description was provided. If this problem persist open a bug report ticket.'}

# SUBMIT

    async def handle_submit(self, description, details, account, role, access_token):
        submit_map = {
            'submit_log_out_request': general_submit_async_functions.submit_log_out_request,
        }

        func = submit_map.get(description)
        if func:
            return await func(access_token)
        
        return {'error': 'Could not process your request, an invalid submit description was provided. If this problem persist open a bug report ticket.'}

# DELETE

    async def handle_delete(self, description, details, account, role, access_token):
        return {'error': 'Could not process your request, an invalid delete description was provided. If this problem persist open a bug report ticket.'}
        delete_map = {}

        func = delete_map.get(description)
        if func:
            if description in ['delete_school_account']:
                response = await func(account, role)
            else:
                response = await func(account, role, details)            
            return response

# CREATE

    async def handle_create(self, description, details, account, role, access_token):
        return {'error': 'Could not process your request, an invalid create description was provided. If this problem persist open a bug report ticket.'}
        create_map = {}

        func = create_map.get(description)
        if func:
            response = await func(account, role, details)
            if description in ['create_account'] and response.get('account'):
                return await general_email_async_functions.send_account_confirmation_email(response['account'])
            return response
        

