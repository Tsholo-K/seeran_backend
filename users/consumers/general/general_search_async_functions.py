# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q
from django.core.cache import cache
from django.utils.translation import gettext as _

# models 
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from grades.models import Grade
from classes.models import Classroom
from email_bans.models import EmailBan
from student_group_timetables.models import StudentGroupTimetable
from daily_schedules.models import DailySchedule
from announcements.models import Announcement
from chats.models import ChatRoom
from activities.models import Activity

# serializers
from users.serializers.general_serializers import DisplayAccountDetailsSerializer, SourceAccountSerializer
from users.serializers.students.students_serializers import  StudentSourceAccountSerializer
from users.serializers.parents.parents_serializers import ParentAccountSerializer
from classes.serializers import ClassSerializer
from email_bans.serializers import EmailBanSerializer
from student_group_timetables.serializers import StudentGroupScheduleSerializer
from daily_schedules.serializers import DailyScheduleSerializer
from daily_schedule_sessions.serializers import DailyScheduleSession
from announcements.serializers import AnnouncementSerializer
from chats.serializers import ChatRoomMessageSerializer
from activities.serializers import ActivitySerializer

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries

# utility functions 
from users import utils as users_utilities
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def search_email_ban(details):
    try:
        # Retrieve the email ban record from the database
        email_ban = EmailBan.objects.get(ban_id=details.get('email_ban'))

        # Determine if a new OTP request can be made
        can_request = not cache.get(details.get('email') + 'email_revalidation_otp')
        
        # Serialize the email ban record
        serialized_email_ban = EmailBanSerializer(email_ban).data
        
        return {"email_ban": serialized_email_ban, "can_request": can_request}
        
    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while retrieving the email ban: {str(e)}'}


@database_sync_to_async
def search_account(user, role, details):
    try:
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

        # Retrieve the base account details of the requested user using the provided account ID.
        requested_user = BaseUser.objects.get(account_id=details.get('account'))

        # Get the appropriate model and related fields for the requested user's role.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[requested_user.role]

        # Build the queryset for the requested account with the necessary related fields.
        requested_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=requested_user.account_id)
        
        # Check if the requesting user has permission to view the requested user's profile or details.
        permission_error = permission_checks.check_profile_or_details_view_permissions(requesting_account, requested_account)
        if permission_error:
            # Return an error message if the requesting user does not have the necessary permissions.
            return permission_error

        # Handle the request based on the reason provided (either 'details' or 'profile').
        if details.get('reason') == 'details':
            # Get the appropriate serializer for the requested user's role.
            Serializer = role_specific_maps.account_details_serializer_mapping[requested_user.role]

            # Serialize the requested user's details and return the serialized data.
            serialized_user = Serializer(instance=requested_account).data

        elif details.get('reason') == 'profile':
            # Serialize the requested user's profile data based on the role.
            if requested_user.role == 'STUDENT':
                serialized_user = StudentSourceAccountSerializer(instance=requested_account).data
            else:
                serialized_user = SourceAccountSerializer(instance=requested_user).data

        else:
            # Return an error message if an invalid reason is provided.
            return {"error": 'Could not process your request, invalid reason provided'}

        # Return the serialized user data if everything is successful.
        return {"user": serialized_user}
               
    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'A parent account with the provided credentials does not exist, please check the account details and try again'}

    except BaseUser.DoesNotExist:
        # Handle the case where the base user account does not exist.
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors and return the error message.
        return {'error': str(e)}


@database_sync_to_async
def search_parents(user, role, details):
    try:
        # Check if the user is requesting their own parents
        if role == 'STUDENT' and user == details.get('account') == 'requesting my own parents':
            # Build the queryset for the requested account with the necessary related fields.
            requesting_account = Student.objects.prefetch_related('parents').get(account_id=details.get('account'))

            parents =  requesting_account.parents.all()

        elif role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT']:
            # Get the appropriate model and related fields (select_related and prefetch_related)
            # for the requesting user's role from the mapping.
            Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

            # Build the queryset for the requested account with the necessary related fields.
            requested_account = Student.objects.select_related('school').prefetch_related('enrolled_classes', 'parents').get(account_id=details.get('account'))
            
            # Check if the requesting user has permission to view the requested user's profile or details.
            permission_error = permission_checks.check_profile_or_details_view_permissions(requesting_account, requested_account)
            if permission_error:
                # Return an error message if the requesting user does not have the necessary permissions.
                return permission_error
        
            parents = requested_account.parents.all().exclude(account_id=requesting_account.account_id) if role == 'PARENT' else requested_account.parents.all()

        else:
            # Return an error message if an invalid reason is provided.
            return {"error": 'could not process your request, your accounts role is invalid'}

        # Serialize the parents to return them in the response
        serialized_parents = ParentAccountSerializer(parents, many=True).data

        return {"parents": serialized_parents}
               
    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'A parent account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors and return the error message.
        return {'error': str(e)}


@database_sync_to_async
def search_class(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}
        
        classroom = None
        
        # Determine the classroom based on the request details
        if details.get('class') == 'requesting my own class' and role == 'TEACHER':
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Teacher.objects.get(account_id=user)

            # Fetch the classroom where the user is the teacher and it is a register class
            classroom = requesting_account.taught_classes.filter(register_class=True).first()
            if classroom is None:
                return {"class": None}

        elif details.get('class'):
            # Get the appropriate model for the requesting user's role from the mapping.
            Model = role_specific_maps.account_access_control_mapping[role]

            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

            # Fetch the specific classroom based on class_id and school
            classroom = Classroom.objects.select_related('school').get(classroom_id=details.get('class'), school=requesting_account.school)
        
            # Check permissions
            permission_error = permission_checks.check_class_permissions(requesting_account, classroom)
            if permission_error:
                return permission_error
        
        else:
            return {"error": 'invalid request'}

        # Serialize and return the classroom data
        serialized_class = ClassSerializer(classroom).data

        return {"class": serialized_class}
               
    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('A classroom with the provided details does not exist. Please check the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_activity(user, role, details):
    try:
        # Retrieve the requesting users account and related attr
        requesting_account = users_utilities.get_account_and_attr(user, role)

        # Retrieve the activity based on the provided activity_id
        activity = Activity.objects.select_related('school', 'logger', 'recipient', 'classroom').get(activity_id=details.get('activity'))

        # Check permissions
        permission_error = permission_checks.check_activity_permissions(requesting_account, activity)
        if permission_error:
            return permission_error
        
        # Serialize the activity data
        serializer = ActivitySerializer(activity).data

        return {"activity": serializer}

    except Activity.DoesNotExist:
        # Handle case where the activity does not exist
        return {'error': 'An activity with the provided ID does not exist. Please check the activity details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_group_schedule_schedules(user, role, details):
    try:
        # Retrieve the requesting users account and related attr
        requesting_account = users_utilities.get_account_and_attr(user, role)
        
        # Retrieve the specified group schedule
        group_schedule = StudentGroupTimetable.objects.select_related('grade__school').prefetch_related('subscribers').get(group_timetable_id=details.get('group_schedule'))

        # Check permissions
        permission_error = permission_checks.check_group_schedule_permissions(requesting_account, group_schedule)
        if permission_error:
            return permission_error

        # Serialize and return the schedules associated with the group schedule
        serialized_schedules = DailyScheduleSerializer(group_schedule.daily_schedules.all(), many=True).data

        return {"schedules": serialized_schedules}
    
    except StudentGroupTimetable.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'a group schedule with the provided credentials does not exist. Please check the group schedule details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_group_schedules(user, role, details):
    try:
        # Ensure the specified role is valid
        if role not in ['ADMIN', 'PRINCIPAL', 'PARENT', 'TEACHER', 'STUDENT']:
            return {"error": "The specified account's role is invalid. please ensure you are attempting to access group schedules from an authorized account."}
        
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        group_schedules = []
        if role in ['ADMIN', 'PRINCIPAL']:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

            if details.get('account'):
                # Retrieve the student
                student = Student.objects.prefetch_related('my_group_schedule').get(account_id=details['account'])
                
                # Retrieve all group schedules associated with the student
                if hasattr(student, 'my_group_schedule'):
                    group_schedules = student.my_group_schedule.all()

                else:
                    return {"schedules": []}
                
            elif details.get('grade'):
                # Retrieve the specified grade
                grade = Grade.objects.get(grade_id=details['grade'], school=requesting_account.school)

                # Retrieve all group schedules associated with the specified grade
                group_schedules = StudentGroupTimetable.objects.filter(grade=grade)

        elif role in ['PARENT']:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.prefetch_related('children').get(account_id=user)

            # Retrieve the student
            student = Student.objects.prefetch_related('my_group_schedule').get(account_id=details['account'])

            if requesting_account.children.filter(account_id=student.account_id).exists():
                return {"error": "unauthorized access. you are only permitted to view group schedules of students who are your children."}
            
            # Retrieve all group schedules associated with the child
            if hasattr(student, 'my_group_schedule'):
                group_schedules = student.my_group_schedule.all()

            else:
                return {"schedules": []}

        elif role in ['STUDENT']:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Student.objects.prefetch_related('my_group_schedule').get(account_id=user)

            # Retrieve all group schedules associated with the account
            if hasattr(requesting_account, 'my_group_schedule'):
                group_schedules = requesting_account.my_group_schedule.all()

            else:
                return {"schedules": []}

        elif role in ['TEACHER']:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.prefetch_related('taught_classes').get(account_id=user)

            # Retrieve the student
            student = Student.objects.prefetch_related('my_group_schedule').get(account_id=details['account'])

            if not requesting_account.taught_classes.filter(students=student).exists():
                return {"error": "unauthorized access. you can only view group schedules of students you teach."}
            
            # Retrieve all group schedules associated with the student
            if hasattr(student, 'my_group_schedule'):
                group_schedules = student.my_group_schedule.all()
            else:
                return {"schedules": []}

        # Serialize the group schedules to return them in the response
        serialized_schedules = StudentGroupScheduleSerializer(group_schedules, many=True).data

        return {"schedules": serialized_schedules}
               
    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'A parent account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'the specified grade does not exist. Please check the grade details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_schedule_sessions(details):
    try:
        schedule = DailySchedule.objects.prefetch_related('sessions').get(schedule_id=details.get('schedule'))
    
        sessions = schedule.sessions.all()

        serialized_sessions = DailyScheduleSession(sessions, many=True).data
        
        return {"sessions": serialized_sessions}
    
    except DailySchedule.DoesNotExist:
        return {"error" : "a schedule with the provided credentials does not exist"}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_announcement(user, role, details):
    try:
        # Validate user role
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            return {"error": "The specified account's role is invalid. Please ensure you are attempting to access an announcement from an authorized account."}
        
        # Retrieve the account making the request
        requesting_user = BaseUser.objects.get(account_id=user)

        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the specified announcement
        announcement = Announcement.objects.select_related('school').get(announcement_id=details.get('announcement_id'))

        # Check access based on user role
        if role == 'PARENT':
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.prefetch_related('children__school').get(account_id=user)

            # Parents can only access announcements related to the schools of their children
            children_schools = requesting_account.children.values_list('school', flat=True)
            if announcement.school.id not in children_schools:
                return {"error": "Unauthorized request. You can only view announcements from schools your children are linked to. Please check announcement details and try again."}
        
        else:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

            # Other roles can only access announcements from their own school
            if announcement.school != requesting_account.school:
                return {"error": "Unauthorized request. You can only view announcements from your own school. Please check announcement details and try again."}

        # Check if the user is already in the reached list and add if not
        if not announcement.reached.filter(pk=requesting_account.pk).exists():
            announcement.reached.add(requesting_user)

        # Serialize and return the announcement data
        serialized_announcement = AnnouncementSerializer(announcement).data

        return {'announcement': serialized_announcement}
               
    except BaseUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}

    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'A parent account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_chat_room(user, role, details):
    try:
        # Retrieve the account making the request
        requesting_user = BaseUser.objects.get(account_id=user)

        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

        # Retrieve the requested user's account
        requested_user = BaseUser.objects.get(account_id=details.get('account'))

        # Get the appropriate model and related fields for the requested user's role.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[requested_user.role]

        # Build the queryset for the requested account with the necessary related fields.
        requested_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=details.get('account'))
        
        # Check permissions
        permission_error = permission_checks.check_message_permissions(requesting_account, requested_account)
        if permission_error:
            return {'error': permission_error}
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=requesting_user, user_two=requested_user) | Q(user_one=requested_user, user_two=requesting_user)).first()
        
        chat_room_exists = bool(chat_room)
        
        serializerd_user = DisplayAccountDetailsSerializer(requested_user).data

        # Serialize the requested user's data
        return {'user': serializerd_user, 'chat': chat_room_exists}

    except BaseUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_chat_room_messages(user, details):
    try:
        # Retrieve the account making the request
        requesting_user = BaseUser.objects.get(account_id=user)
        requested_user = BaseUser.objects.get(account_id=details.get('account'))
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=requesting_user, user_two=requested_user) | Q(user_one=requested_user, user_two=requesting_user)).select_related('user_one', 'user_two').first()
        
        if not chat_room:
            return {"not_found": 'No such chat room exists'}
        
        # Retrieve the cursor from the request
        cursor = details.get('cursor')
        if cursor:
            # Fetch messages before the cursor with a limit of 20
            messages = chat_room.messages.filter(timestamp__lt=cursor).order_by('-timestamp')[:20]
        else:
            # Fetch the latest 20 messages
            messages = chat_room.messages.order_by('-timestamp')[:20]

        if not messages.exists():
            return {'messages': [], 'next_cursor': None, 'unread_messages': 0}

        # Convert messages to a list and reverse for correct ascending order
        messages = list(messages)[::-1]

        # Serialize the messages
        serialized_messages = ChatRoomMessageSerializer(messages, many=True, context={'user': user}).data
        
        # Determine the next cursor
        next_cursor = messages[0].timestamp.isoformat() if len(messages) > 19 else None

        # Mark unread messages as read and count them in one query
        unread_messages = chat_room.messages.filter(read_receipt=False).exclude(sender=requesting_user)

        # Check if there are any messages that match the criteria
        unread_count = unread_messages.count()
        if unread_count > 0:
            # Mark the messages as read
            unread_messages.update(read_receipt=True)
            return {'messages': serialized_messages, 'next_cursor': next_cursor, 'unread_messages': unread_count, 'user': str(requested_user.account_id), 'chat': str(requesting_user.account_id)}
        
        else:
            # Handle the case where no messages need to be updated
            return {'messages': serialized_messages, 'next_cursor': next_cursor, 'unread_messages': 0}

    except BaseUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except ChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}
    
    except Exception as e:
        return {'error': str(e)}

