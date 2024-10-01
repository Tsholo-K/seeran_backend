# python
import json

# channels
from channels.generic.websocket import AsyncWebsocketConsumer

# websocket manager
from seeran_backend.middleware import  connection_manager

# utility functions
from authentication.utils import validate_access_token

# admin async functions 
from . import admin_connect_async_functions
from . import admin_create_async_functions
from . import admin_view_async_functions
from . import admin_update_async_functions
from . import admin_delete_async_functions
from . import admin_search_async_functions
from . import admin_submit_async_functions
from . import admin_assign_async_functions
from . import admin_form_data_async_functions
from . import admin_link_async_functions
from . import admin_unlink_async_functions

# general async functions
from websockets.consumers.general import general_message_async_functions
from websockets.consumers.general import general_submit_async_functions
from websockets.consumers.general import general_update_async_functions
from websockets.consumers.general import general_search_async_functions
from websockets.consumers.general import general_view_async_functions
from websockets.consumers.general import general_verify_async_functions
from websockets.consumers.general import general_email_async_functions


class AdminConsumer(AsyncWebsocketConsumer):

# CONNECT

    async def connect(self):
        # Get the user's role from the scope
        role = self.scope['role']

        # Check if the user has the required role
        if role not in ['ADMIN', 'PRINCIPAL']:
            return await self.close()

        account = self.scope['account']

        await self.accept()

        response = await admin_connect_async_functions.account_details(account)
        if 'error' in response or 'denied' in response:
            await self.send(text_data=json.dumps(response))
            return await self.close()

        await connection_manager.connect(account, self)
        await self.send(text_data=json.dumps(response))

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
        
        if action == 'INSPECT' and description == 'socket_communication_check':
            return await self.send(text_data=json.dumps({'socket_communication_successful': True}))

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
            'FORM DATA': self.handle_form_data,
            'UPDATE': self.handle_update,
            'MESSAGE': self.handle_message,
            'SUBMIT': self.handle_submit,
            'ASSIGN': self.handle_assign,
            'DELETE': self.handle_delete,
            'LINK': self.handle_link,
            'UNLINK': self.handle_unlink,
            'CREATE': self.handle_create,
        }

        handler = action_map.get(action)
        if handler:
            return await handler(description, details, user, role, access_token)
        
        return {'error': 'Could not process your request, an invalid action was provided. If this problem persist open a bug report ticket.'}

# VIEW

    async def handle_view(self, description, details, user, role, access_token):
        view_map = {
            'view_my_security_information': general_view_async_functions.view_my_security_information,
            'view_my_email_address_status_information': general_view_async_functions.view_my_email_address_status_information,

            'view_chat_rooms': general_view_async_functions.view_chat_rooms,

            'view_school_details': admin_view_async_functions.view_school_details,

            'view_school_announcements': admin_view_async_functions.view_school_announcements,
        }

        func = view_map.get(description)
        if func:
            if description in ['view_chat_rooms', 'view_my_email_address_status_information']:
                return await func(user)
            else:
                return await func(user, role)

        return {'error': 'Could not process your request, an invalid view description was provided. If this problem persist open a bug report ticket.'}

# SEARCH

    async def handle_search(self, description, details, user, role, access_token):
        search_map = {
            'search_email_ban': general_search_async_functions.search_email_ban,

            'search_chat_room': general_search_async_functions.search_chat_room,
            'search_chat_room_messages': general_search_async_functions.search_chat_room_messages,

            'search_audit_entries': admin_search_async_functions.search_audit_entries,
            'search_audit_entry': admin_search_async_functions.search_audit_entry,

            'search_permission_groups': admin_search_async_functions.search_permission_groups,
            'search_permission_group': admin_search_async_functions.search_permission_group,

            'search_permission_group_subscribers': admin_search_async_functions.search_permission_group_subscribers,

            'search_accounts': admin_search_async_functions.search_accounts,
            'search_students': admin_search_async_functions.search_students,
            'search_parents': admin_search_async_functions.search_parents,

            'search_account': admin_search_async_functions.search_account,

            'search_announcement': admin_search_async_functions.search_announcement,

            'search_grades': admin_search_async_functions.search_grades,
            'search_grade': admin_search_async_functions.search_grade,
            'search_grade_details': admin_search_async_functions.search_grade_details,
            'search_grade_register_classrooms': admin_search_async_functions.search_grade_register_classrooms,

            'search_subject': admin_search_async_functions.search_subject,
            'search_subject_details': admin_search_async_functions.search_subject_details,

            'search_grade_terms': admin_search_async_functions.search_grade_terms,
            'search_term_details': admin_search_async_functions.search_term_details,
            'search_term_subject_performance': admin_search_async_functions.search_term_subject_performance,

            'search_classrooms': admin_search_async_functions.search_classrooms,
            'search_teacher_classrooms': admin_search_async_functions.search_teacher_classrooms,

            'search_month_attendance_records': admin_search_async_functions.search_month_attendance_records,

            'search_assessments': admin_search_async_functions.search_assessments,
            'search_assessment': admin_search_async_functions.search_assessment,

            'search_transcripts': admin_search_async_functions.search_transcripts,
            'search_transcript': admin_search_async_functions.search_transcript,

            'search_student_classroom_card': admin_search_async_functions.search_student_classroom_card,
            'search_activity': admin_search_async_functions.search_activity,

            'search_teacher_schedule_schedules': admin_search_async_functions.search_teacher_timetable_schedules,

            'search_group_timetables': admin_search_async_functions.search_group_timetables,
            'search_group_timetable_schedules': admin_search_async_functions.search_group_timetable_schedules,
            'search_group_timetable_subscribers': admin_search_async_functions.search_group_timetable_subscribers,

            'search_schedule_sessions': admin_search_async_functions.search_timetable_sessions,
        }

        func = search_map.get(description)
        
        if func:
            if description in ['search_email_ban']:
                response = await func(details) 
            elif description in ['search_chat_room_messages']:
                response = await func(user, details)
            else:
                response =  await func(user, role, details)

            if description in ['search_chat_room_messages'] and response.get('user'):
                await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                await connection_manager.send_message(user, json.dumps({'unread_messages': response['unread_messages']}))

                return {'messages': response['messages'], 'next_cursor': response['next_cursor']}  

            return response

        return {'error': 'Could not process your request, an invalid search description was provided. If this problem persist open a bug report ticket.'}


# ASSIGN

    async def handle_assign(self, description, details, user, role, access_token):
        assign_map = {
            'assign_permission_group_subscribers': admin_assign_async_functions.assign_permission_group_subscribers,
        }

        func = assign_map.get(description)
        if func:
            response =  await func(user, role, details)
            return response

        return {'error': 'Could not process your request, an invalid search description was provided. If this problem persist open a bug report ticket.'}

# VERIFY

    async def handle_verify(self, description, details, user, role, access_token):
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
                response = await func(user, details)

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

    async def handle_form_data(self, description, details, user, role, access_token):
        form_data_map = {
            'form_data_for_creating_classroom': admin_form_data_async_functions.form_data_for_creating_classroom,
            'form_data_for_updating_classroom': admin_form_data_async_functions.form_data_for_updating_classroom,

            'form_data_for_adding_students_to_classroom': admin_form_data_async_functions.form_data_for_adding_students_to_classroom,

            'form_data_for_classroom_attendance_register': admin_form_data_async_functions.form_data_for_classroom_attendance_register,

            'form_data_for_setting_assessment' : admin_form_data_async_functions.form_data_for_setting_assessment,
            'form_data_for_updating_assessment' : admin_form_data_async_functions.form_data_for_updating_assessment,

            'form_data_for_collecting_assessment_submissions' : admin_form_data_async_functions.form_data_for_collecting_assessment_submissions,
            'form_data_for_assessment_submissions' : admin_form_data_async_functions.form_data_for_assessment_submissions,
            'form_data_for_assessment_submission_details' : admin_form_data_async_functions.form_data_for_assessment_submission_details,

            'form_data_for_adding_students_to_group_schedule': admin_form_data_async_functions.form_data_for_adding_students_to_group_schedule,
        }

        func = form_data_map.get(description)
        if func:
            response = await func(user, role, details)
            return response
        
        return {'error': 'Could not process your request, an invalid form data description was provided. If this problem persist open a bug report ticket.'}

# UPDATE

    async def handle_update(self, description, details, user, role, access_token):
        update_map = {
            'update_email_address': general_update_async_functions.update_email_address,
            'update_password': general_update_async_functions.update_password,

            'update_multi_factor_authentication': general_update_async_functions.update_multi_factor_authentication,

            'update_school_account_details' : admin_update_async_functions.update_school_account_account,

            'update_account_details': admin_update_async_functions.update_account_details,
            
            'update_grade_details' : admin_update_async_functions.update_grade_details,
            
            'update_subject_details' : admin_update_async_functions.update_subject_details,

            'update_term_details' : admin_update_async_functions.update_term_details,

            'update_assessment' : admin_update_async_functions.update_assessment,
            'update_assessment_as_collected' : admin_update_async_functions.update_assessment_as_collected,
            'update_assessment_as_graded' : admin_update_async_functions.update_assessment_as_graded,

            'update_student_grade' : admin_update_async_functions.update_student_transcript_score,
            
            'update_messages_as_read': general_update_async_functions.update_messages_as_read,

            'update_classroom_details': admin_update_async_functions.update_classroom_details,
            'update_classroom_students': admin_update_async_functions.update_classroom_students,
        }

        func = update_map.get(description)
        if func:
            if description in ['update_email_address', 'update_password']:
                response = await func(user, role, details, access_token)
            elif description in ['update_multi_factor_authentication', 'update_messages_as_read']:
                response = await func(user, details)
            else:
                response = await func(user, role, details)

            if response.get('user'):
                if description in ['update_messages_as_read']:
                    await connection_manager.send_message(response['user'], json.dumps({'description': 'read_receipt', 'chat': response['chat']}))
                    return {'message': 'read receipt sent'}
                
            return response
        
        return {'error': 'Could not process your request, an invalid update description was provided. If this problem persist open a bug report ticket.'}

# MESSAGE

    async def handle_message(self, description, details, user, role, access_token):
        message_map = {
            'message_private': general_message_async_functions.message_private,
        }

        func = message_map.get(description)
        if func:
            response = await func(user, role, details)
            if response.get('reciever'):
                if description in ['message_private']:
                    await connection_manager.send_message(response['recipient']['account_id'], json.dumps({'description': 'text_message', 'message': response['message'], 'author': response['author']}))
                    await connection_manager.send_message(response['author']['account_id'], json.dumps({'description': 'text_message_fan', 'message': response['message'], 'recipient': response['recipient']}))

                    return {'message': 'private message successfully sent'}
            
        return {'error': 'Could not process your request, an invalid text description was provided. If this problem persist open a bug report ticket.'}

# SUBMIT

    async def handle_submit(self, description, details, user, role, access_token):
        submit_map = {
            'submit_assessment_submissions' : admin_submit_async_functions.submit_assessment_submissions,

            'submit_attendance': admin_submit_async_functions.submit_school_attendance,

            'submit_log_out_request': general_submit_async_functions.submit_log_out_request,
        }

        func = submit_map.get(description)
        if func:
            if description in ['submit_log_out_request']:
                response = await func(access_token)
            else:
                response = await func(user, role, details)            
            return response
        
        return {'error': 'Could not process your request, an invalid submit description was provided. If this problem persist open a bug report ticket.'}

# DELETE

    async def handle_delete(self, description, details, user, role, access_token):
        delete_map = {
            'delete_school_account': admin_delete_async_functions.delete_school_account,

            'delete_account': admin_delete_async_functions.delete_account,

            'delete_grade': admin_delete_async_functions.delete_grade,

            'delete_class': admin_delete_async_functions.delete_class,
            
            'delete_assessment': admin_delete_async_functions.delete_assessment,
            
            'delete_schedule': admin_delete_async_functions.delete_daily_schedule,

            'delete_group_schedule': admin_delete_async_functions.delete_group_schedule,
        }

        func = delete_map.get(description)
        if func:
            response = await func(user, role, details)            
            return response
        
        return {'error': 'Could not process your request, an invalid delete description was provided. If this problem persist open a bug report ticket.'}

# LINK

    async def handle_link(self, description, details, user, role, access_token):
        link_map = {
            'link_parent': admin_link_async_functions.link_parent,
        }

        func = link_map.get(description)
        if func:
            response = await func(user, role, details)
            if response.get('user'):
                return await general_email_async_functions.send_account_confirmation_email(response['user'])
            return response
        
        return {'error': 'Could not process your request, an invalid link description was provided. If this problem persist open a bug report ticket.'}

# UNLINK

    async def handle_unlink(self, description, details, user, role, access_token):
        unlink_map = {
            'unlink_parent': admin_unlink_async_functions.unlink_parent,
        }

        func = unlink_map.get(description)
        if func:
            response = await func(user, role, details)            
            return response
        
        return {'error': 'Could not process your request, an invalid unlink description was provided. If this problem persist open a bug report ticket.'}

# CREATE

    async def handle_create(self, description, details, user, role, access_token):
        create_map = {
            'create_account': admin_create_async_functions.create_account,
            
            'create_permission_group': admin_create_async_functions.create_permission_group,

            'create_term': admin_create_async_functions.create_term,

            'create_grade': admin_create_async_functions.create_grade,

            'create_subject': admin_create_async_functions.create_subject,

            'create_classroom': admin_create_async_functions.create_classroom,
            
            'create_assessment': admin_create_async_functions.create_assessment,

            'create_timetable': admin_create_async_functions.create_timetable,

            'create_group_timetable': admin_create_async_functions.create_group_timetable,

            'create_announcement': admin_create_async_functions.create_announcement,
        }

        func = create_map.get(description)
        if func:
            response = await func(user, role, details)
            if description in ['create_account'] and response.get('user'):
                return await general_email_async_functions.send_account_confirmation_email(response['user'])
            return response
        
        return {'error': 'Could not process your request, an invalid create description was provided. If this problem persist open a bug report ticket.'}







