# python
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# websocket manager
from seeran_backend.middleware import  connection_manager

# utility functions
from authentication.utils import validate_access_token

# async functions 
from users.consumers import general_async_functions
from . import teacher_async_functions


class TeacherConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role not in ['TEACHER']:
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
            return await self.send(text_data=json.dumps({'error': 'request not authenticated.. access denied'}))

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

    async def handle_request(self, action, description, details, user, access_token):
        action_map = {
            'GET': self.handle_get,
            'SEARCH': self.handle_search,
            'VERIFY': self.handle_verify,
            'FORM DATA': self.handle_form_data,
            'PUT': self.handle_put,
            'POST': self.handle_post,
        }

        handler = action_map.get(action)
        if handler:
            return await handler(description, details, user, access_token)
        
        return {'error': 'Invalid action'}

    async def handle_get(self, description, details, user, access_token):
        get_map = {
            'my_security_information': general_async_functions.fetch_my_security_information,
            'email_information': general_async_functions.fetch_my_email_information,

            'chats': general_async_functions.fetch_chats,

            'announcements': general_async_functions.fetch_announcements,

            'log_out': general_async_functions.log_out,
        }

        func = get_map.get(description)
        if func:
            return await func(user) if description != 'log_out' else await func(access_token)
        
        return {'error': 'Invalid get description'}

    async def handle_search(self, description, details, user, access_token):
        search_map = {
            'parents': general_async_functions.search_parents,

            'account_profile': general_async_functions.search_account_profile,
            'account_id': general_async_functions.search_account_id,

            'teacher_classes': general_async_functions.search_teacher_classes,

            'teacher_schedule_schedules': general_async_functions.search_teacher_schedule_schedules,
            'group_schedule_schedules': general_async_functions.search_group_schedule_schedules,
            'group_schedules': general_async_functions.search_group_schedules,
            'schedule_sessions': general_async_functions.search_for_schedule_sessions,

            'month_attendance_records': general_async_functions.search_month_attendance_records,

            'announcement': general_async_functions.search_announcement,

            'chat_room': general_async_functions.search_chat_room,
            'chat_room_messages': general_async_functions.search_chat_room_messages,

            'class': general_async_functions.search_class,

            'email_ban': general_async_functions.search_my_email_ban,
        }

        func = search_map.get(description)
        
        if func:
            response = await func(details) if description in ['schedule_sessions'] else await func(user, details)
            
            if response.get('user') and description in ['chat_room_messages']:
                await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                response = {'messages': response['messages'], 'next_cursor': response['next_cursor']}

            return response
        
        return {'error': 'Invalid search description'}

    async def handle_verify(self, description, details, user, access_token):
        verify_map = {
            'verify_email': general_async_functions.verify_email,
            'verify_password': general_async_functions.verify_password,
            'verify_otp': general_async_functions.verify_otp,
            'verify_email_revalidation_otp': general_async_functions.verify_email_revalidate_otp,
        }

        func = verify_map.get(description)
        if func:
            response = await func(details) if description == 'verify_email' else await func(user, details)
            if response.get('user'):
                if description == 'verify_email' or description == 'verify_password':
                    return await general_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your request.')
                if description == 'verify_email_revalidation_otp':
                    return await general_async_functions.send_email_revalidation_one_time_pin_email(response.get('user'))
            return response
        
        return {'error': 'Invalid verify description'}

    async def handle_form_data(self, description, details, user, access_token):
        form_data_map = {
            'attendance_register': general_async_functions.form_data_for_attendance_register,
        }

        func = form_data_map.get(description)
        if func:
            response = await func(user, details)
            return response
        
        return {'error': 'Invalid form data description'}

    async def handle_put(self, description, details, user, access_token):
        put_map = {
            'update_email': general_async_functions.update_email,
            'update_password': general_async_functions.update_password,

            'update_multi_factor_authentication': general_async_functions.update_multi_factor_authentication,

            'mark_messages_as_read': general_async_functions.mark_messages_as_read,

            'send_email_revalidation_otp': general_async_functions.validate_email_revalidation,
        }

        func = put_map.get(description)
        if func:
            response = await func(user, details, access_token) if description in ['update_email', 'update_password'] else await func(user, details)
                        
            if response.get('user') and description in ['mark_messages_as_read']:
                await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))

                return {'message': 'read receipt sent'}

            if description == 'send_email_revalidation_otp' and response.get('user'):
                response = await general_async_functions.send_email_revalidation_one_time_pin_email(response.get('user'))

                if response.get('message'):
                    return await general_async_functions.update_email_ban_otp_sends(details)
                
            return response
        
        return {'error': 'Invalid put description'}

    async def handle_post(self, description, details, user, access_token):
        post_map = {
            'text': general_async_functions.text,

            'submit_absentes': general_async_functions.submit_absentes,
            'submit_late_arrivals': general_async_functions.submit_late_arrivals,
            
            'log_activity': general_async_functions.log_activity,
        }

        func = post_map.get(description)

        if func:
            response = await func(user, details)
            
            if response.get('reciever') and description in ['text']:
                await connection_manager.send_message(response['reciever']['id'], json.dumps({'description': 'text_message', 'message': response['message'], 'sender': response['sender']}))
                await connection_manager.send_message(response['sender']['id'], json.dumps({'description': 'text_message_fan', 'message': response['message'], 'reciever': response['reciever']}))

                return {'message': 'text message sent'}

            return response 
        
        return {'error': 'Invalid post description'}
