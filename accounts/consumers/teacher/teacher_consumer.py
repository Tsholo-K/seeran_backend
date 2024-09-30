# python
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# websocket manager
from seeran_backend.middleware import connection_manager

# utility functions
from authentication.utils import validate_access_token

# admin async functions 
from . import teacher_post_async_functions
from . import teacher_search_async_functions
from . import teacher_form_data_async_functions

# general async functions 
from accounts.consumers.general import general_submit_async_functions
from accounts.consumers.general import general_put_async_functions
from accounts.consumers.general import general_search_async_functions
from accounts.consumers.general import general_view_async_functions
from accounts.consumers.general import general_verify_async_functions
from accounts.consumers.general import general_email_async_functions


class TeacherConsumer(AsyncWebsocketConsumer):

# CONNECT

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role not in ['TEACHER']:
            return await self.close()
                
        account_id = self.scope['user']
        await connection_manager.connect(account_id, self)

        await self.accept()

# DISCONNECT

    async def disconnect(self, close_code):
        account_id = self.scope['user']
        await connection_manager.disconnect(account_id, self)
        
# RECIEVE

    async def receive(self, text_data):
        user = self.scope.get('user')
        role = self.scope.get('role')
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
        
        if action == 'AUTHENTICATE' and description == 'socket_authentication':
            return await self.send(text_data=json.dumps({'authenticated': 'socket connection valid and authenticated'}))

        response = await self.handle_request(action, description, details, user, role, access_token)
        
        if response is not None:
            return await self.send(text_data=json.dumps(response))
        
        return await self.send(text_data=json.dumps({'error': 'provided information is invalid.. request revoked'}))

# HANDLER/ROUTER

    async def handle_request(self, action, description, details, user, role, access_token):
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
            return await handler(description, details, user, role, access_token)
        
        return {'error': 'Invalid action'}

# GET

    async def handle_get(self, description, details, user, role, access_token):
        get_map = {
            'my_security_information': general_view_async_functions.fetch_security_information,
            'email_information': general_view_async_functions.fetch_email_information,

            'chats': general_view_async_functions.fetch_chats,

            'announcements': general_view_async_functions.fetch_announcements,
        }

        func = get_map.get(description)
        if func:
            if description in ['chats', 'email_information']:
                return await func(user)
            else:
                return await func(user, role)
        
        return {'error': 'Invalid get description'}

# SEARCH

    async def handle_search(self, description, details, user, role, access_token):
        search_map = {
            'account': general_search_async_functions.search_account,
            
            'parents': general_search_async_functions.search_parents,

            'announcement': general_search_async_functions.search_announcement,

            'teacher_classes': teacher_search_async_functions.search_teacher_classes,
            'class': general_search_async_functions.search_class,

            'assessments': teacher_search_async_functions.search_assessments,

            'student_class_card': teacher_search_async_functions.search_student_class_card,
            'activity': general_search_async_functions.search_activity,

            'teacher_schedule_schedules': teacher_search_async_functions.search_teacher_schedule_schedules,

            'group_schedules': general_search_async_functions.search_group_schedules,
            'group_schedule_schedules': general_search_async_functions.search_group_schedule_schedules,

            'schedule_sessions': general_search_async_functions.search_schedule_sessions,

            'month_attendance_records': teacher_search_async_functions.search_month_attendance_records,

            'chat_room': general_search_async_functions.search_chat_room,
            'chat_room_messages': general_search_async_functions.search_chat_room_messages,

            'email_ban': general_search_async_functions.search_email_ban,
        }

        func = search_map.get(description)
        if func:
            if description in ['schedule_sessions', 'email_ban']:
                response = await func(details) 
            elif description in ['chat_room_messages', 'assessments']:
                response = await func(user, details)
            elif description in ['teacher_classes']:
                response = await func(user)
            else:
                response =  await func(user, role, details)
                        
            if response.get('user') and description in ['chat_room_messages']:
                await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                await connection_manager.send_message(user, json.dumps({'unread_messages': response['unread_messages']} ))

                response = {'messages': response['messages'], 'next_cursor': response['next_cursor']}  

            return response
        
        return {'error': 'Invalid search description'}

# VERIFY

    async def handle_verify(self, description, details, user, role, access_token):
        verify_map = {
            'verify_email': general_verify_async_functions.verify_email,
            'verify_password': general_verify_async_functions.verify_password,

            'verify_otp': general_verify_async_functions.verify_otp,
            
            'verify_email_revalidation_otp': general_verify_async_functions.verify_email_revalidate_otp,

            'send_email_revalidation_otp': general_verify_async_functions.validate_email_revalidation,
        }

        func = verify_map.get(description)
        if func:
            if description == 'verify_email':
                response = await func(details)  
            else:
                response = await func(user, details)

            if response.get('user'):
                if description in ['verify_email', 'verify_password']:
                    return await general_email_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your request.')
                elif description in ['verify_email_revalidation_otp']:
                    return await general_email_async_functions.send_email_revalidation_one_time_pin_email(response.get('user'))
                
            return response
        
        return {'error': 'Invalid verify description'}

# FORM DATA

    async def handle_form_data(self, description, details, user, role, access_token):
        form_data_map = {
            'attendance_register': teacher_form_data_async_functions.form_data_for_attendance_register,

            'set_assessment' : teacher_form_data_async_functions.form_data_for_setting_assessment,
            'update_assessment' : teacher_form_data_async_functions.form_data_for_updating_assessment,
        }

        func = form_data_map.get(description)
        if func:
            response = await func(user, details)

            return response
        
        return {'error': 'Invalid form data description'}

# PUT

    async def handle_put(self, description, details, user, role, access_token):
        put_map = {
            'update_email': general_put_async_functions.update_email,
            'update_password': general_put_async_functions.update_password,

            'update_multi_factor_authentication': general_put_async_functions.update_multi_factor_authentication,

            'mark_messages_as_read': general_put_async_functions.mark_messages_as_read,
        }

        func = put_map.get(description)
        if func:
            if description in ['update_email', 'update_password']:
                response = await func(user, role, details, access_token)
            elif description in ['update_multi_factor_authentication', 'mark_messages_as_read']:
                response = await func(user, details)
            else:
                response = await func(user, role, details)
                        
            if response.get('user'):
                if description in ['mark_messages_as_read']:
                    await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                    return {'message': 'read receipt sent'}

                elif description in ['send_email_revalidation_otp']:
                    response = await general_email_async_functions.send_email_revalidation_one_time_pin_email(response['user'])

                    if response.get('message'):
                        return await general_put_async_functions.update_email_ban_otp_sends(details)
                
            return response
        
        return {'error': 'Invalid put description'}

# POST

    async def handle_post(self, description, details, user, role, access_token):
        post_map = {
            'text': general_submit_async_functions.text,

            'submit_attendance': teacher_post_async_functions.submit_attendance,
            
            'log_activity': teacher_post_async_functions.log_activity,
            
            'create_assessment': teacher_post_async_functions.set_assessment,

            'log_out': general_submit_async_functions.log_out,
        }

        func = post_map.get(description)

        if func:
            if description in ['log_out']:
                response = await func(access_token)
            elif description in ['create_assessment', 'log_activity', 'submit_attendance']:
                response = await func(user, details)
            else:
                response = await func(user, role, details)
            
            if description in ['text'] and response.get('reciever'):
                await connection_manager.send_message(response['reciever']['account_id'], json.dumps({'description': 'text_message', 'message': response['message'], 'sender': response['sender']}))
                await connection_manager.send_message(response['sender']['account_id'], json.dumps({'description': 'text_message_fan', 'message': response['message'], 'reciever': response['reciever']}))

                return {'message': 'text message sent'}

            return response 
        
        return {'error': 'Invalid post description'}