# python
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# utility functions
from authentication.utils import validate_access_token

# async functions 
from users.consumers import general_async_functions
from . import admin_async_functions

class AdminConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope.get('role')

        # Check if the user has the required role
        if role not in ['ADMIN', 'PRINCIPAL']:
            return await self.close()
        
        await self.accept()
        return await self.send(text_data=json.dumps({'message': 'Welcome Back'}))

    async def disconnect(self, close_code):
        pass

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

            'grades': admin_async_functions.fetch_grades,
            'grades_with_student_count': admin_async_functions.fetch_grades_with_student_count,

            'announcements': general_async_functions.fetch_announcements,

            'log_out': general_async_functions.log_out,
        }

        func = get_map.get(description)
        if func:
            return await func(user) if description != 'log_me_out' else await func(access_token)
        
        return {'error': 'Invalid get description'}

    async def handle_search(self, description, details, user, access_token):
        search_map = {
            'accounts': admin_async_functions.search_accounts,
            'students': admin_async_functions.search_students,
            'parents': general_async_functions.search_parents,

            'subscribed_students': admin_async_functions.search_subscribed_students,

            'account_profile': general_async_functions.search_account_profile,
            'account_id': general_async_functions.search_account_id,

            'teacher_schedule_schedules': general_async_functions.search_teacher_schedule_schedules,
            'group_schedule_schedules': general_async_functions.search_group_schedule_schedules,
            'group_schedules': general_async_functions.search_group_schedules,
            'schedule_sessions': general_async_functions.search_for_schedule_sessions,

            'teacher_classes': admin_async_functions.search_teacher_classes,
            'register_classes': admin_async_functions.search_grade_register_classes,

            'month_attendance_records': general_async_functions.search_month_attendance_records,

            'announcement': general_async_functions.search_announcement,

            'grade': admin_async_functions.search_grade,
            'subject': admin_async_functions.search_subject,
            'class': admin_async_functions.search_class,

            'email_ban': general_async_functions.search_my_email_ban,
        }

        func = search_map.get(description)
        
        if func:
            response = await func(details) if description in ['schedule_sessions'] else await func(user, details)
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

            'class_creation': admin_async_functions.form_data_for_class_creation,
            'class_update': admin_async_functions.form_data_for_class_update,

            'add_students_to_register_class': admin_async_functions.form_data_for_adding_students_to_register_class,
            'add_students_to_subject_class': admin_async_functions.form_data_for_adding_students_to_subject_class,

            'attendance_register': general_async_functions.form_data_for_attendance_register,

            'add_students_to_group_schedule': admin_async_functions.form_data_add_students_to_group_schedule,
        }

        func = form_data_map.get(description)
        if func:
            response = await func(user) if description in ['class_creation'] else await func(user, details)
            return response
        
        return {'error': 'Invalid form data description'}

    async def handle_put(self, description, details, user, access_token):
        put_map = {
            'update_email': general_async_functions.update_email,
            'update_password': general_async_functions.update_password,

            'update_multi_factor_authentication': general_async_functions.update_multi_factor_authentication,

            'update_account': admin_async_functions.update_account,

            'update_class': admin_async_functions.update_class,

            'send_email_revalidation_otp': general_async_functions.validate_email_revalidation,
        }

        func = put_map.get(description)
        if func:
            response = await func(user, details, access_token) if description in ['update_email', 'update_password'] else await func(user, details)
            
            if description == 'send_email_revalidation_otp' and response.get('user'):
                response = await general_async_functions.send_email_revalidation_one_time_pin_email(response.get('user'))

                if response.get('message'):
                    return await general_async_functions.update_email_ban_otp_sends(details)
                
            return response
        
        return {'error': 'Invalid put description'}

    async def handle_post(self, description, details, user, access_token):
        post_map = {
            'create_account': admin_async_functions.create_account,
            'create_student_account': admin_async_functions.create_student_account,
            'link_parent': admin_async_functions.link_parent,
            'delete_account': admin_async_functions.delete_account,
            'unlink_parent': admin_async_functions.unlink_parent,

            'create_grade': admin_async_functions.create_grade,
            'create_subjects': admin_async_functions.create_subjects,

            'create_class': admin_async_functions.create_class,
            'add_students_to_class': admin_async_functions.add_students_to_class,
            'remove_student_from_class': admin_async_functions.remove_student_from_class,
            'delete_class': admin_async_functions.delete_class,

            'create_schedule': admin_async_functions.create_schedule,
            'delete_schedule': admin_async_functions.delete_schedule,

            'create_group_schedule': admin_async_functions.create_group_schedule,
            'add_students_to_group_schedule': admin_async_functions.add_students_to_group_schedule,
            'remove_students_from_group_schedule': admin_async_functions.remove_students_from_group_schedule,
            'delete_group_schedule': admin_async_functions.delete_group_schedule,

            'announce': admin_async_functions.announce,

            'submit_absentes': general_async_functions.submit_absentes,
            'submit_late_arrivals': general_async_functions.submit_late_arrivals,
        }

        func = post_map.get(description)

        if func:
            response = await func(user, details)

            if response.get('user') and description in ['create_account', 'create_student_account', 'link_parent']:
                return await general_async_functions.send_account_confirmation_email(response.get('user'))
            
            return response
        
        return {'error': 'Invalid post description'}
