# python
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# websocket manager
from seeran_backend.middleware import  connection_manager

# utility functions
from authentication.utils import validate_access_token

# admin async functions 
from . import admin_post_async_functions
from . import admin_put_async_functions
from . import admin_search_async_functions
from . import admin_get_async_functions
from . import admin_form_data_async_functions

# general async functions 
from users.consumers.general import general_post_async_functions
from users.consumers.general import general_put_async_functions
from users.consumers.general import general_search_async_functions
from users.consumers.general import general_get_async_functions
from users.consumers.general import general_verify_async_functions
from users.consumers.general import general_email_async_functions
from users.consumers.general import general_form_data_async_functions


class AdminConsumer(AsyncWebsocketConsumer):

# CONNECT

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role not in ['ADMIN', 'PRINCIPAL']:
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

        if not (user and role and access_token and validate_access_token(access_token)):
            await self.send(text_data=json.dumps({'error': 'request not authenticated.. access denied'}))
            return await self.close()

        data = json.loads(text_data)
        action = data.get('action')
        description = data.get('description')
        details = data.get('details')

        if not action or not description:
            return await self.send(text_data=json.dumps({'error': 'invalid request..'}))
        
        if action == 'AUTHENTICATE' and description == 'socket_authentication':
            return await self.send(text_data=json.dumps({'authenticated': 'socket connection valid andauthenticated'}))

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
            'my_security_information': general_get_async_functions.fetch_security_information,
            'email_information': general_get_async_functions.fetch_email_information,

            'chats': general_get_async_functions.fetch_chats,

            'announcements': general_get_async_functions.fetch_announcements,
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
            "school_details": admin_search_async_functions.search_school_details,

            "audit_entries": admin_search_async_functions.search_audit_entries,
            "audit_entry": admin_search_async_functions.search_audit_entry,

            'accounts': admin_search_async_functions.search_accounts,
            'students': admin_search_async_functions.search_students,
            'parents': general_search_async_functions.search_parents,

            'account': general_search_async_functions.search_account,

            'announcement': general_search_async_functions.search_announcement,

            'grades': admin_search_async_functions.search_grades,
            'grade': admin_search_async_functions.search_grade,
            "grade_details": admin_search_async_functions.search_grade_details,

            'subject': admin_search_async_functions.search_subject,
            "subject_details": admin_search_async_functions.search_subject_details,

            "terms": admin_search_async_functions.search_grade_terms,
            'term_details': admin_search_async_functions.search_term_details,

            'teacher_classes': admin_search_async_functions.search_teacher_classes,
            'register_classes': admin_search_async_functions.search_grade_register_classes,

            'class': general_search_async_functions.search_class,

            'assessments': admin_search_async_functions.search_assessments,
            'assessment': admin_search_async_functions.search_assessment,

            'student_class_card': admin_search_async_functions.search_student_class_card,
            'activity': general_search_async_functions.search_activity,

            'teacher_schedule_schedules': admin_search_async_functions.search_teacher_schedule_schedules,

            'group_schedules': general_search_async_functions.search_group_schedules,
            'group_schedule_schedules': general_search_async_functions.search_group_schedule_schedules,
            'subscribed_students': admin_search_async_functions.search_subscribed_students,

            'schedule_sessions': general_search_async_functions.search_schedule_sessions,

            'month_attendance_records': admin_search_async_functions.search_month_attendance_records,

            'chat_room': general_search_async_functions.search_chat_room,
            'chat_room_messages': general_search_async_functions.search_chat_room_messages,

            'email_ban': general_search_async_functions.search_email_ban,
        }

        func = search_map.get(description)
        
        if func:
            if description in ['schedule_sessions', 'email_ban']:
                response = await func(details) 
            elif description in ['chat_room_messages']:
                response = await func(user, details)
            elif description in ['school_details']:
                response = await func(user, role)
            else:
                response =  await func(user, role, details)
            
            if description in ['chat_room_messages'] and response.get('user'):
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
                        
            'send_email_revalidation_otp': general_verify_async_functions.validate_email_revalidation,
            'verify_email_revalidation_otp': general_verify_async_functions.verify_email_revalidate_otp,
        }

        func = verify_map.get(description)
        if func:
            if description in ['verify_email']:
                response = await func(role, details)
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
            'class_creation': admin_form_data_async_functions.form_data_for_creating_class,
            'class_update': admin_form_data_async_functions.form_data_for_updating_class,

            'add_students_to_class': admin_form_data_async_functions.form_data_for_adding_students_to_class,

            'attendance_register': general_form_data_async_functions.form_data_for_attendance_register,

            'set_assessment' : general_form_data_async_functions.form_data_for_assessment_setting,

            'add_students_to_group_schedule': admin_form_data_async_functions.form_data_for_adding_students_to_group_schedule,
        }

        func = form_data_map.get(description)
        if func:
            response = await func(user, role, details)

            return response
        
        return {'error': 'Invalid form data description'}

# PUT

    async def handle_put(self, description, details, user, role, access_token):
        put_map = {
            'update_email': general_put_async_functions.update_email,
            'update_password': general_put_async_functions.update_password,

            'update_multi_factor_authentication': general_put_async_functions.update_multi_factor_authentication,

            'update_school_details' : admin_put_async_functions.update_school_account,
            
            'update_grade_details' : admin_put_async_functions.update_grade_details,
            
            'update_subject_details' : admin_put_async_functions.update_subject_details,

            'update_term_details' : admin_put_async_functions.update_term_details,

            'mark_messages_as_read': general_put_async_functions.mark_messages_as_read,

            'update_account': admin_put_async_functions.update_account,

            'update_class': admin_put_async_functions.update_class,
            'update_class_students': admin_put_async_functions.update_class_students,
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
            'delete_school_account': admin_post_async_functions.delete_school_account,

            'create_account': admin_post_async_functions.create_account,
            'delete_account': admin_post_async_functions.delete_account,

            'link_parent': admin_post_async_functions.link_parent,
            'unlink_parent': admin_post_async_functions.unlink_parent,

            'create_term': admin_post_async_functions.create_term,

            'create_grade': admin_post_async_functions.create_grade,
            'delete_grade': admin_post_async_functions.delete_grade,

            'create_subject': admin_post_async_functions.create_subject,

            'create_class': admin_post_async_functions.create_class,
            'delete_class': admin_post_async_functions.delete_class,
            
            'create_assessment': admin_post_async_functions.set_assessment,

            'create_schedule': admin_post_async_functions.create_daily_schedule,
            'delete_schedule': admin_post_async_functions.delete_daily_schedule,

            'create_group_schedule': admin_post_async_functions.create_group_timetable,
            'delete_group_schedule': admin_post_async_functions.delete_group_schedule,

            'announce': admin_post_async_functions.announce,

            'text': general_post_async_functions.text,

            'submit_attendance': admin_post_async_functions.submit_attendance,
            
            'log_out': general_post_async_functions.log_out,
        }

        func = post_map.get(description)
        if func:
            if description in ['log_out']:
                response = await func(access_token)
            else:
                response = await func(user, role, details)

            if description in ['text'] and response.get('reciever'):
                await connection_manager.send_message(response['reciever']['account_id'], json.dumps({'description': 'text_message', 'message': response['message'], 'sender': response['sender']}))
                await connection_manager.send_message(response['sender']['account_id'], json.dumps({'description': 'text_message_fan', 'message': response['message'], 'reciever': response['reciever']}))

                return {'message': 'text message sent'}

            elif description in ['create_account', 'link_parent'] and response.get('user'):
                return await general_email_async_functions.send_account_confirmation_email(response['user'])
            
            return response
        
        return {'error': 'Invalid post description'}
