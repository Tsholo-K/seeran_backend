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

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role not in ['ADMIN', 'PRINCIPAL']:
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


    async def handle_get(self, description, details, user, role, access_token):
        get_map = {
            'my_security_information': general_get_async_functions.fetch_my_security_information,
            'email_information': general_get_async_functions.fetch_my_email_information,

            'grades': admin_get_async_functions.fetch_grades,
            'student_grades': admin_get_async_functions.fetch_student_grades,

            'chats': general_get_async_functions.fetch_chats,

            'announcements': general_get_async_functions.fetch_announcements,
        }

        func = get_map.get(description)
        if func:
            return await func(user, role)
        
        return {'error': 'Invalid get description'}


    async def handle_search(self, description, details, user, role, access_token):
        search_map = {
            "school_details": general_search_async_functions.search_school_details,

            'accounts': admin_search_async_functions.search_accounts,
            'students': admin_search_async_functions.search_students,
            'parents': general_search_async_functions.search_parents,

            'account': general_search_async_functions.search_account,

            "grade_details": admin_search_async_functions.search_grade_details,

            "subject_details": admin_search_async_functions.search_subject_details,

            "grade_terms": admin_search_async_functions.search_grade_terms,
            'term_details': admin_search_async_functions.search_term_details,

            'teacher_schedule_schedules': general_search_async_functions.search_teacher_schedule_schedules,
            'group_schedule_schedules': general_search_async_functions.search_group_schedule_schedules,
            'group_schedules': general_search_async_functions.search_group_schedules,
            'schedule_sessions': general_search_async_functions.search_for_schedule_sessions,

            'subscribed_students': admin_search_async_functions.search_subscribed_students,

            'teacher_classes': general_search_async_functions.search_teacher_classes,
            'register_classes': admin_search_async_functions.search_grade_register_classes,

            'month_attendance_records': general_search_async_functions.search_month_attendance_records,

            'announcement': general_search_async_functions.search_announcement,

            'chat_room': general_search_async_functions.search_chat_room,
            'chat_room_messages': general_search_async_functions.search_chat_room_messages,

            'grade': admin_search_async_functions.search_grade,
            'subject': admin_search_async_functions.search_subject,

            'class': general_search_async_functions.search_class,
            'student_class_card': general_search_async_functions.search_student_class_card,

            'activity': general_search_async_functions.search_activity,

            'email_ban': general_search_async_functions.search_my_email_ban,
        }

        func = search_map.get(description)
        
        if func:
            response = await func(role, details) if description in ['schedule_sessions'] else await func(user, role, details)
            
            if response.get('user') and description in ['chat_room_messages']:
                await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                await connection_manager.send_message(user, json.dumps({'unread_messages': response['unread_messages']} ))
                response = {'messages': response['messages'], 'next_cursor': response['next_cursor']}  

            return response
        
        return {'error': 'Invalid search description'}


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
            response = await func(role, details) if description == 'verify_email' else await func(user, role, details)
            if response.get('user'):
                if description == 'verify_email' or description == 'verify_password':
                    return await general_email_async_functions.send_one_time_pin_email(response.get('user'), reason='This OTP was generated in response to your request.')
                if description == 'verify_email_revalidation_otp':
                    return await general_email_async_functions.send_email_revalidation_one_time_pin_email(response.get('user'))
            return response
        
        return {'error': 'Invalid verify description'}


    async def handle_form_data(self, description, details, user, role, access_token):
        form_data_map = {
            'class_creation': admin_form_data_async_functions.form_data_for_creating_class,
            'class_update': admin_form_data_async_functions.form_data_for_updating_class,

            'add_students_to_class': admin_form_data_async_functions.form_data_for_adding_students_to_class,

            'attendance_register': general_form_data_async_functions.form_data_for_attendance_register,

            'add_students_to_group_schedule': admin_form_data_async_functions.form_data_for_adding_students_to_group_schedule,
        }

        func = form_data_map.get(description)
        if func:
            response = await func(user, role, details)
            return response
        
        return {'error': 'Invalid form data description'}


    async def handle_put(self, description, details, user, role, access_token):
        put_map = {
            'update_email': general_put_async_functions.update_email,
            'update_password': general_put_async_functions.update_password,

            'update_multi_factor_authentication': general_put_async_functions.update_multi_factor_authentication,

            'update_school_details' : general_put_async_functions.update_school_details,
            
            'update_grade_details' : admin_put_async_functions.update_grade_details,
            
            'update_subject_details' : admin_put_async_functions.update_subject_details,

            'update_term_details' : admin_put_async_functions.update_term_details,

            'mark_messages_as_read': general_put_async_functions.mark_messages_as_read,

            'update_account': admin_put_async_functions.update_account,

            'update_class': admin_put_async_functions.update_class,
            'update_class_students': admin_put_async_functions.update_class_students,

            'add_students_to_group_schedule': admin_put_async_functions.add_students_to_group_schedule,
            'remove_students_from_group_schedule': admin_put_async_functions.remove_students_from_group_schedule,
        }

        func = put_map.get(description)
        if func:
            response = await func(user, role, details, access_token) if description in ['update_email', 'update_password'] else await func(user, role, details)
  
            if response.get('user'):
                if description in ['mark_messages_as_read']:
                    await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))

                    return {'message': 'read receipt sent'}

                elif description in ['send_email_revalidation_otp']:
                    response = await general_email_async_functions.send_email_revalidation_one_time_pin_email(response.get('user'))

                    if response.get('message'):
                        return await general_put_async_functions.update_email_ban_otp_sends(details)
                
            return response
        
        return {'error': 'Invalid put description'}


    async def handle_post(self, description, details, user, role, access_token):
        post_map = {
            'delete_school_account': general_post_async_functions.delete_school_account,

            'create_account': admin_post_async_functions.create_account,
            'delete_account': admin_post_async_functions.delete_account,

            'link_parent': admin_post_async_functions.link_parent,
            'unlink_parent': admin_post_async_functions.unlink_parent,

            'create_term': admin_post_async_functions.create_term,

            'create_grade': admin_post_async_functions.create_grade,
            'create_subject': admin_post_async_functions.create_subject,

            'create_class': admin_post_async_functions.create_class,
            'delete_class': admin_post_async_functions.delete_class,

            'create_schedule': admin_post_async_functions.create_schedule,
            'delete_schedule': admin_post_async_functions.delete_schedule,

            'create_group_schedule': admin_post_async_functions.create_group_schedule,
            'delete_group_schedule': admin_post_async_functions.delete_group_schedule,

            'announce': admin_post_async_functions.announce,

            'text': general_post_async_functions.text,

            'submit_absentes': general_post_async_functions.submit_absentes,
            'submit_late_arrivals': general_post_async_functions.submit_late_arrivals,
            
            'log_out': general_post_async_functions.log_out,
        }

        func = post_map.get(description)

        if func:
            response = await func(access_token) if description in ['log_out'] else await func(user, role, details)

            if response.get('reciever') and description in ['text']:
                await connection_manager.send_message(response['reciever']['id'], json.dumps({'description': 'text_message', 'message': response['message'], 'sender': response['sender']}))
                await connection_manager.send_message(response['sender']['id'], json.dumps({'description': 'text_message_fan', 'message': response['message'], 'reciever': response['reciever']}))

                return {'message': 'text message sent'}

            elif response.get('user') and description in ['create_admin_account', 'create_teacher_account', 'create_student_account', 'link_parent']:
                return await general_email_async_functions.send_account_confirmation_email(response['user'])
            
            return response
        
        return {'error': 'Invalid post description'}
