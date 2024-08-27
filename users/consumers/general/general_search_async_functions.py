# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q
from django.core.cache import cache
from django.utils.translation import gettext as _

# simple jwt

# models 
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from schools.models import School
from grades.models import Grade
from classes.models import Classroom
from email_bans.models import EmailBan
from schedules.models import Schedule, TeacherSchedule, GroupSchedule
from attendances.models import Absent, Late
from announcements.models import Announcement
from chats.models import ChatRoom, ChatRoomMessage
from activities.models import Activity

# serializers
from users.serializers.general_serializers import DisplayAccountDetailsSerializer, SourceAccountSerializer
from users.serializers.principals.principals_serializers import PrincipalAccountDetailsSerializer
from users.serializers.admins.admins_serializers import AdminAccountDetailsSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountDetailsSerializer
from users.serializers.students.students_serializers import LeastAccountDetailsSerializer, StudentSourceAccountSerializer, StudentAccountDetailsSerializer
from users.serializers.parents.parents_serializers import ParentAccountSerializer, ParentAccountDetailsSerializer
from schools.serializers import SchoolDetailsSerializer
from classes.serializers import TeacherClassesSerializer, ClassSerializer
from email_bans.serializers import EmailBanSerializer
from schedules.serializers import ScheduleSerializer, GroupScheduleSerializer, SessoinsSerializer
from announcements.serializers import AnnouncementSerializer
from chats.serializers import ChatRoomMessageSerializer
from activities.serializers import ActivitiesSerializer, ActivitySerializer

# utility functions 
from attendances.utility_functions import get_month_dates

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries


@database_sync_to_async
def search_my_email_ban(details):
    """
    Retrieves information about a specific email ban based on the provided details.

    This function fetches the details of an email ban using the provided `email_ban_id` and checks
    whether a new OTP can be requested for the given email. 

    Args:
        details (dict): A dictionary containing:
            - 'email_ban_id': The ID of the email ban to be retrieved.
            - 'email': The email address to check if OTP can be requested.

    Returns:
        dict: A dictionary containing:
            - 'email_ban': Serialized data of the email ban if it exists.
            - 'can_request': A boolean indicating whether a new OTP request is allowed.
            - 'error': A string containing an error message if an exception is raised.

    Raises:
        EmailBan.DoesNotExist: If no email ban is found with the provided ID.
        Exception: For any other unexpected errors.

    Example:
        response = await search_my_email_ban({'email_ban_id': 123, 'email': 'user@example.com'})
        if 'error' in response:
            # Handle error
        else:
            email_ban_info = response
            # Process email ban information
    """
    try:
        # Retrieve the email ban record from the database
        email_ban = EmailBan.objects.get(ban_id=details.get('email_ban_id'))

        # Determine if a new OTP request can be made
        can_request = not cache.get(details.get('email') + 'email_revalidation_otp')
        
        # Serialize the email ban record
        serializer = EmailBanSerializer(email_ban)
        
        return {"email_ban": serializer.data, "can_request": can_request}
        
    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while retrieving the email ban: {str(e)}'}
    
    
@database_sync_to_async
def search_school_details(user, role, details):
    try:
        if role not in ['FOUNDER', 'PRINCIPAL', 'ADMIN']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        if details.get('school') == 'requesting my own school':
            # Retrieve the user and related school in a single query using select_related
            if role == 'PRINCIPAL':
                admin = Principal.objects.select_related('school').only('school').get(account_id=user)
            else:
                admin = Admin.objects.select_related('school').only('school').get(account_id=user)

            # Serialize the school object into a dictionary
            serialized_school = SchoolDetailsSerializer(admin.school).data
        
        else:
            school = School.objects.get(school_id=details.get('school'))

            # Serialize the school object into a dictionary
            serialized_school = SchoolDetailsSerializer(instance=school).data

        return {"school": serialized_school}
                   
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except School.DoesNotExist:
        # Handle the case where the provided school ID does not exist
        return {"error": "a school with the provided credentials does not exist"}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_account(user, role, details):
    """
    Retrieves the account details or profile of a requested user based on the account ID and role provided.
    This function dynamically handles different roles and fetches the necessary related data based on the 
    role-specific requirements.

    Parameters:
    - user: The account ID of the requesting user.
    - role: The role of the requesting user (e.g., 'PARENT', 'PRINCIPAL', etc.).
    - details: A dictionary containing the account ID of the requested user and the reason for the request 
      (e.g., 'details' or 'profile').

    Returns:
    - A dictionary containing the serialized user data or an error message if the operation fails.
    """

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
def search_teacher_classes(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        if details.get('teacher') == 'requesting my own classes' and role == 'TEACHER':
            requesting_account = Model.objects.prefetch_related('taught_classes').get(account_id=user)
            classes = requesting_account.taught_classes.exclude(register_class=True)

        elif role in ['ADMIN', 'PRINCIPAL']:
            requesting_account = Model.objects.select_related('school').get(account_id=user)
            teacher = Teacher.objects.prefetch_related('taught_classes').get(account_id=details['teacher'], school=requesting_account.school)

            classes = teacher.taught_classes

        serializer = TeacherClassesSerializer(classes, many=True)

        return {"classes": serializer.data}
               
    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_class(user, details):
    """
    Searches for a classroom based on the user's role and provided details.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the search criteria, such as 'class_id'.

    Returns:
        dict: A dictionary containing the search results or error messages.
    """
    try:
        # Retrieve the user account
        account = BaseUser.objects.select_related('school').get(account_id=user)

        # Determine the classroom based on the request details
        if details.get('class') == 'requesting_my_own_class':
            # Fetch the classroom where the user is the teacher and it is a register class
            classroom = Classroom.objects.select_related('school').filter(teacher=account, register_class=True).first()
            if classroom is None:
                return {"class": None}

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": _("Unauthorized access. The account making the request has an invalid role or the classroom is not from your school.")}

        else:
            # Fetch the specific classroom based on class_id and school
            classroom = Classroom.objects.get(class_id=details.get('class'), school=account.school)
        
        # Check permissions
        permission_error = permission_checks.check_class_permissions(account, classroom)
        if permission_error:
            return permission_error

        # Serialize and return the classroom data
        serializer = ClassSerializer(classroom)
        return {"class": serializer.data}

    except BaseUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': _('An account with the provided credentials does not exist. Please check the account details and try again.')}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('A classroom with the provided details does not exist. Please check the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_class_card(user, details):

    try:
        # Retrieve the account making the request
        account = BaseUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        student = BaseUser.objects.get(account_id=details.get('account_id'))

        # Check permissions
        permission_error = permission_checks.check_profile_or_details_view_permissions(account, student)
        if permission_error:
            return permission_error
        
        # Determine the classroom based on the request details
        if details.get('class') == 'requesting_my_own_class':
            # Fetch the classroom where the user is the teacher and it is a register class
            classroom = Classroom.objects.select_related('school').filter(teacher=account, register_class=True).first()
            if classroom is None:
                return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": _("could not proccess your request. the account making the request has an invalid role or the classroom is not from your school")}

        else:
            # Fetch the specific classroom based on class_id and school
            classroom = Classroom.objects.get(class_id=details.get('class'))

            if account.school != classroom.school:
                return {"error": "could not proccess your request. you are not permitted to view information about classses outside your own school"}

        # retrieve the students activities 
        activities = Activity.objects.filter(classroom=classroom, recipient=student)

        return {"user": SourceAccountSerializer(instance=student).data, 'activities' : ActivitiesSerializer(activities, many=True).data}

    except BaseUser.DoesNotExist:
        # Handle case where the user or requested user account does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}
        
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_activity(user, details):
    """
    Search for an activity by its ID and check if the user has the necessary permissions to access it.

    Args:
        user (int): The ID of the user making the request.
        details (dict): A dictionary containing the details of the activity being requested, including the 'activity_id'.

    Returns:
        dict: A dictionary containing the serialized activity data if the user has permission,
              or an error message if there was an issue.
    """
    try:
        # Retrieve the account making the request
        account = BaseUser.objects.select_related('school').get(account_id=user)

        # Retrieve the activity based on the provided activity_id
        activity = Activity.objects.select_related('school', 'logger', 'recipient', 'classroom').get(activity_id=details.get('activity_id'))

        # Check permissions
        permission_error = permission_checks.check_activity_permissions(account, activity)
        if permission_error:
            return permission_error
        
        # Serialize the activity data
        serializer = ActivitySerializer(activity).data

        return {"activity": serializer}

    except BaseUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}

    except Activity.DoesNotExist:
        # Handle case where the activity does not exist
        return {'error': 'An activity with the provided ID does not exist. Please check the activity details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_teacher_schedule_schedules(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        if details.get('teacher') == 'requesting my own schedules' and role == 'TEACHER':
            teacher = Model.objects.prefetch_related('teacher_schedule__schedules').get(account_id=user)

        elif role in ['ADMIN', 'PRINCIPAL']:
            requesting_account = Model.objects.select_related('school').get(account_id=user)
            teacher = Teacher.objects.prefetch_related('teacher_schedule__schedules').get(account_id=details['teacher'], school=requesting_account.school)

        # Check if the teacher has a schedule
        if hasattr(teacher, 'teacher_schedule'):
            schedules = teacher.teacher_schedule.schedules.all()
        else:
            return {'schedules': []}
        
        # Serialize the schedules to return them in the response
        serializer = ScheduleSerializer(schedules, many=True)

        return {"schedules": serializer.data}
               
    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_group_schedule_schedules(user, details):
    """
    Function to search and retrieve weekly schedules for a specific group schedule.

    This function performs the following steps:
    1. Retrieve the account making the request.
    2. Retrieve the specified group schedule.
    3. Check permissions based on the user's role:
       - Founders are not allowed to access group schedules.
       - Students can only access schedules if they are subscribed to the group schedule.
       - Parents can only access schedules if at least one of their children is subscribed to the group schedule.
       - Teachers, Admins, and Principals can only access schedules if they belong to the same school as the group schedule's grade.
    4. Serialize and return the schedules associated with the group schedule.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the group_schedule_id to identify the group schedule.

    Returns:
        dict: A dictionary containing either the schedules or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        GroupSchedule.DoesNotExist: If the group schedule with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await search_group_schedule_schedules(request.user.account_id, {'group_schedule_id': 'GS123'})
        if 'error' in response:
            # Handle error
        else:
            schedules = response['schedules']
            # Process schedules
    """
    try:
        # Retrieve the account making the request
        account = BaseUser.objects.get(account_id=user)
        
        # Retrieve the specified group schedule
        group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'))

        # Check permissions for various roles

        # Founders are not allowed to access group schedules
        if account.role == 'FOUNDER':
            return {"error": "Founders are not authorized to access group schedules"}

        # Students can only access schedules if they are in the group schedule's students
        if account.role == 'STUDENT' and account not in group_schedule.students.all():
            return {"error": "As a student, you can only view schedules for group schedules you are subscribed to. Please check your group schedule assignments and try again"}

        # Parents can only access schedules if at least one of their children is in the group schedule's students
        if account.role == 'PARENT' and not any(child in group_schedule.students.all() for child in account.children.all()):
            return {"error": "As a parent, you can only view schedules for group schedules that your children are subscribed to. Please check your child's group schedule assignments and try again"}

        # Teachers, Admins, and Principals can only access schedules if they belong to the same school as the group schedule's grade
        if account.role in ['TEACHER', 'ADMIN', 'PRINCIPAL'] and account.school != group_schedule.grade.school:
            return {"error": "You can only view schedules for group schedules within your own school. Please check the group schedule and try again"}

        # Serialize and return the schedules associated with the group schedule
        serializer = ScheduleSerializer(group_schedule.schedules.all(), many=True)
        return {"schedules": serializer.data}
    
    except BaseUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again'}
    
    except GroupSchedule.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'a group schedule with the provided credentials does not exist. Please check the group schedule details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_group_schedules(user, details):
    """
    Function to search and retrieve group schedules for a specific grade or student.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the grade_id to identify the grade.

    Returns:
        dict: A dictionary containing either the group schedules or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Grade.DoesNotExist: If the grade with the provided ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = BaseUser.objects.get(account_id=user)
        
        # Ensure the specified role is valid
        if account.role not in ['ADMIN', 'PRINCIPAL', 'PARENT', 'TEACHER', 'STUDENT']:
            return {"error": "The specified account's role is invalid. please ensure you are attempting to access group schedules from an authorized account."}

        group_schedules = []

        if account.role in ['ADMIN', 'PRINCIPAL']:
            if details.get('account_id'):
                # Retrieve the student
                student = BaseUser.objects.get(account_id=details.get('account_id'))

                if student.role != 'STUDENT' or account.school != student.school:
                    return {"error": "unauthorized access. you can only view group schedules of students in your school."}
                
                # Retrieve all group schedules associated with the student
                if hasattr(student, 'my_group_schedule'):
                    group_schedules = student.my_group_schedule.all()
                else:
                    return {"schedules": []}
                
            if details.get('grade_id'):
                # Retrieve the specified grade
                grade = Grade.objects.get(grade_id=details.get('grade_id'))

                # Ensure the specified grade belongs to the same school as the account's school
                if account.school != grade.school:
                    return {"error": "the specified grade does not belong to your school. please ensure you are attempting to access group schedules for a grade in your own school."}

                # Retrieve all group schedules associated with the specified grade
                group_schedules = GroupSchedule.objects.filter(grade=grade)

        if account.role in ['PARENT']:
            # Retrieve the account's child
            child = BaseUser.objects.get(account_id=details.get('account_id'))

            if child.role != 'STUDENT' or child not in account.children.all():
                return {"error": "unauthorized access. you are only permitted to view group schedules of students who are your children."}
            
            # Retrieve all group schedules associated with the child
            if hasattr(child, 'my_group_schedule'):
                group_schedules = child.my_group_schedule.all()
            else:
                return {"schedules": []}

        if account.role in ['STUDENT']:
            # Retrieve all group schedules associated with the account
            if hasattr(account, 'my_group_schedule'):
                group_schedules = account.my_group_schedule.all()
            else:
                return {"schedules": []}

        if account.role in ['TEACHER']:
            # Retrieve the student
            student = BaseUser.objects.get(account_id=details.get('account_id'))

            if student.role != 'STUDENT' or not account.taught_classes.filter(students=student).exists():
                return {"error": "unauthorized access. you can only view group schedules of students you teach."}
            
            # Retrieve all group schedules associated with the student
            if hasattr(student, 'my_group_schedule'):
                group_schedules = student.my_group_schedule.all()
            else:
                return {"schedules": []}

        # Serialize the group schedules to return them in the response
        serializer = GroupScheduleSerializer(group_schedules, many=True)
        return {"schedules": serializer.data}
    
    except BaseUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Grade.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'the specified grade does not exist. Please check the grade details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_schedule_sessions(details):

    try:
        schedule = Schedule.objects.prefetch_related('sessions').get(schedule_id=details.get('schedule'))
    
        sessions = schedule.sessions.all()
        serialized_sessions = SessoinsSerializer(sessions, many=True).data
        
        return {"sessions": serialized_sessions}
    
    except Schedule.DoesNotExist:
        return {"error" : "a schedule with the provided credentials does not exist"}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_month_attendance_records(user, details):

    try:
        account = BaseUser.objects.get(account_id=user)
 
        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.get(teacher=account, register_class=True, school=account.school)

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can view the attendance records for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school, register_class=True)
        
        start_date, end_date = get_month_dates(details.get('month_name'))

        # Query for the Absent instances where absentes is True
        absents = Absent.objects.prefetch_related('absent_students').filter(Q(date__gte=start_date) & Q(date__lt=end_date) & Q(classroom=classroom) & Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for absent in absents:
            late = Late.objects.prefetch_related('late_students').filter(date__date=absent.date.date(), classroom=classroom).first()
            record = {
                'date': absent.date.isoformat(),
                'absent_students': LeastAccountDetailsSerializer(absent.absent_students.all(), many=True).data,
                'late_students': LeastAccountDetailsSerializer(late.late_students.all(), many=True).data if late else [],
            }
            attendance_records.append(record)

        return {'records': attendance_records}
               
    except BaseUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'a classroom in your school with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_announcement(user, details):
    """
    Function to search and retrieve a specific announcement based on user role and permissions.

    This function checks the user's role and school association to determine if they have the appropriate
    permissions to access the announcement. The function also verifies that the announcement belongs to 
    a school associated with the user.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the `announcement_id` to identify the specific announcement.

    Returns:
        dict: A dictionary containing either the requested announcement data or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user or announcement with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await search_announcement(request.user.account_id, {'announcement_id': 'AN123'})
        if 'error' in response:
            # Handle error
        else:
            announcement_data = response['announcement']
            # Process announcement data
    """
    try:
        # Retrieve the user account making the request
        account = BaseUser.objects.get(account_id=user)

        # Validate user role
        if account.role not in ['PARENT', 'STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL']:
            return {"error": "The specified account's role is invalid. Please ensure you are attempting to access an announcement from an authorized account."}

        # Retrieve the specified announcement
        announcement = Announcement.objects.get(announcement_id=details.get('announcement_id'))

        # Check access based on user role
        if account.role == 'PARENT':
            # Parents can only access announcements related to the schools of their children
            children_schools = account.children.values_list('school', flat=True)
            if announcement.school.id not in children_schools:
                return {"error": "Unauthorized request. You can only view announcements from schools your children are linked to. Please check announcement details and try again."}
        else:
            # Other roles can only access announcements from their own school
            if announcement.school != account.school:
                return {"error": "Unauthorized request. You can only view announcements from your own school. Please check announcement details and try again."}

        # Check if the user is already in the reached list and add if not
        if not announcement.reached.filter(pk=account.pk).exists():
            announcement.reached.add(account)

        # Serialize and return the announcement data
        serializer = AnnouncementSerializer(announcement)
        return {'announcement': serializer.data}

    except BaseUser.DoesNotExist:
        # Handle case where the user or announcement does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_chat_room(user, details):
    try:
        # Retrieve the account making the request
        requesting_account = BaseUser.objects.get(account_id=user)

        # Retrieve the requested user's account
        requested_account = BaseUser.objects.get(account_id=details.get('account_id'))
        
        # Check permissions
        permission_error = permission_checks.check_message_permissions(requesting_account, requested_account)
        if permission_error:
            return {'error': permission_error}
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=requesting_account, user_two=requested_account) | Q(user_one=requested_account, user_two=requesting_account)).first()
        
        chat_room_exists = bool(chat_room)
        
        serializerd_user = DisplayAccountDetailsSerializer(requested_account).data

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
    """
    Fetch messages from a chat room with pagination support and mark unread messages as read.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the details of the request, including:
            - 'chatroom_id' (str): The ID of the chat room.
            - 'cursor' (str, optional): The timestamp to fetch messages before.

    Returns:
        dict: A dictionary containing the serialized messages and the next cursor for pagination, or an error message.
    """
    try:
        # Retrieve the account making the request
        account = BaseUser.objects.get(account_id=user)
        requested_user = BaseUser.objects.get(account_id=details.get('account_id'))
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=account, user_two=requested_user) | Q(user_one=requested_user, user_two=account)).select_related('user_one', 'user_two').first()
        
        if not chat_room:
            return {"not_found": 'No such chat room exists'}
        
        # Retrieve the cursor from the request
        cursor = details.get('cursor')
        if cursor:
            # Fetch messages before the cursor with a limit of 20
            messages = ChatRoomMessage.objects.filter(chat_room=chat_room, timestamp__lt=cursor).order_by('-timestamp')[:20]
        else:
            # Fetch the latest 20 messages
            messages = ChatRoomMessage.objects.filter(chat_room=chat_room).order_by('-timestamp')[:20]

        if not messages.exists():
            return {'messages': [], 'next_cursor': None, 'unread_messages': 0}

        # Convert messages to a list and reverse for correct ascending order
        messages = list(messages)[::-1]

        # Serialize the messages
        serializer = ChatRoomMessageSerializer(messages, many=True, context={'user': user})
        
        # Determine the next cursor
        next_cursor = messages[0].timestamp.isoformat() if len(messages) > 19 else None

        # Mark unread messages as read and count them in one query
        unread_messages = ChatRoomMessage.objects.filter(chat_room=chat_room, read_receipt=False).exclude(sender=account)

        # Check if there are any messages that match the criteria
        unread_count = unread_messages.count()
        if unread_count > 0:
            # Mark the messages as read
            unread_messages.update(read_receipt=True)
            return {'messages': serializer.data, 'next_cursor': next_cursor, 'unread_messages': unread_count, 'user': str(requested_user.account_id), 'chat': str(account.account_id)}
        
        else:
            # Handle the case where no messages need to be updated
            return {'messages': serializer.data, 'next_cursor': next_cursor, 'unread_messages': 0}

    except BaseUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except ChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}
    
    except Exception as e:
        return {'error': str(e)}

