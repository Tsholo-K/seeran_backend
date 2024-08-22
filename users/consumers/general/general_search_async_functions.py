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
from users.models import CustomUser
from email_bans.models import EmailBan
from timetables.models import Schedule, TeacherSchedule, GroupSchedule
from classes.models import Classroom
from attendances.models import Absent, Late
from grades.models import Grade
from announcements.models import Announcement
from chats.models import ChatRoom, ChatRoomMessage
from activities.models import Activity

# serializers
from users.serializers import AccountSerializer, StudentAccountAttendanceRecordSerializer, AccountProfileSerializer, AccountIDSerializer, ChatroomSerializer, BySerializer
from email_bans.serializers import EmailBanSerializer
from timetables.serializers import SessoinsSerializer, ScheduleSerializer
from timetables.serializers import GroupScheduleSerializer
from announcements.serializers import AnnouncementSerializer
from chats.serializers import ChatRoomMessageSerializer
from classes.serializers import TeacherClassesSerializer, ClassSerializer
from activities.serializers import ActivitiesSerializer, ActivitySerializer

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email
from attendances.utility_functions import get_month_dates

# checks
from users.checks import permission_checks


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
def search_account_profile(user, details):
    """
    Function to search and retrieve the profile of a user based on the access control logic.

    This function performs the following steps:
    1. Retrieve the account making the request.
    2. Retrieve the requested user's account.
    3. Check permissions using the `check_profile_or_id_view_permissions` function.
    4. Serialize and return the requested user's profile.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the account_id of the requested user.

    Returns:
        dict: A dictionary containing either the requested user's profile data or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user or requested user with the provided account ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await search_account_profile(request.user.account_id, {'account_id': 'U123'})
        if 'error' in response:
            # Handle error
        else:
            profile = response['user']
            # Process profile
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        requested_user = CustomUser.objects.get(account_id=details.get('account_id'))
        
        # Check permissions
        permission_error = permission_checks.check_profile_or_id_view_permissions(account, requested_user)
        if permission_error:
            return permission_error

        # Serialize the requested user's profile to return it in the response
        serializer = AccountProfileSerializer(instance=requested_user)
        return {"user": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user or requested user account does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_account_id(user, details):
    """
    Function to search and retrieve the account ID of a user based on the access control logic.

    This function performs the following steps:
    1. Retrieve the account making the request.
    2. Retrieve the requested user's account.
    3. Check permissions using the `check_profile_or_id_view_permissions` function.
    4. Serialize and return the requested user's account ID.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the account_id of the requested user.

    Returns:
        dict: A dictionary containing either the requested user's account ID or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user or requested user with the provided account ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await search_account_id(request.user.account_id, {'account_id': 'U123'})
        if 'error' in response:
            # Handle error
        else:
            account_id = response['user']
            # Process account ID
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        requested_user = CustomUser.objects.get(account_id=details.get('account_id'))
        
        # Check permissions
        permission_error = permission_checks.check_profile_or_id_view_permissions(account, requested_user)
        if permission_error:
            return permission_error
        
        # Serialize the requested user's account ID to return it in the response
        serializer = AccountIDSerializer(instance=requested_user)
        return {"user": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user or requested user account does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_parents(user, details):
    """
    Function to search and retrieve the parents of a specific student.

    This function performs the following steps:
    1. Determine if the user is requesting their own parents or the parents of another student.
    2. Retrieve the student's account and validate their role.
    3. Verify the requester's permissions:
       - Students can request their own parents.
       - Admins and Principals from the same school can access a student's parents.
       - Teachers can access the parents of students they teach.
       - Parents can access their own children's parents but cannot access parents of other students.
    4. Retrieve and serialize the parents associated with the student.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the account_id of the student.

    Returns:
        dict: A dictionary containing either the parents or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user or student with the provided account ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await search_parents(request.user.account_id, {'account_id': 'S123'})
        if 'error' in response:
            # Handle error
        else:
            parents = response['parents']
            # Process parents
    """
    try:
        # Check if the user is requesting their own parents
        if user == details.get('account_id'):
            student = CustomUser.objects.get(account_id=user)

            if student.role != 'STUDENT':
                return {"error": "Unauthorized request.. permission denied"}

        else:
            # Retrieve the account making the request
            account = CustomUser.objects.get(account_id=user)
            # Retrieve the student's account
            student = CustomUser.objects.get(account_id=details.get('account_id'))

            # Ensure the requester's role and permissions
            if account.role not in ['ADMIN', 'PRINCIPAL', 'TEACHER', 'PARENT']:
                return {"error": "Invalid role for request.. permission denied"}
            
            if student.role != 'STUDENT':
                return {"error": "Unauthorized request.. permission denied"}

            if account.role in ['ADMIN', 'PRINCIPAL'] and account.school != student.school:
                return {"error": "Unauthorized request.. permission denied"}
                
            if account.role == 'TEACHER' and not account.taught_classes.filter(students=student).exists():
                return {"error": "Unauthorized access.. permission denied"}
                
            if account.role == 'PARENT' and account not in student.children.all():
                return {"error": "Unauthorized access.. permission denied"}

            parents = CustomUser.objects.filter(children=student, role='PARENT').exclude(account) if account.role == 'PARENT' else CustomUser.objects.filter(children=student, role='PARENT')

        # Serialize the parents to return them in the response
        serializer = AccountSerializer(parents, many=True)
        return {"parents": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

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
        account = CustomUser.objects.select_related('school').get(account_id=user)

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

    except CustomUser.DoesNotExist:
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
        account = CustomUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        student = CustomUser.objects.get(account_id=details.get('account_id'))

        # Check permissions
        permission_error = permission_checks.check_profile_or_id_view_permissions(account, student)
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

        return {"user": BySerializer(instance=student).data, 'activities' : ActivitiesSerializer(activities, many=True).data}

    except CustomUser.DoesNotExist:
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
        account = CustomUser.objects.select_related('school').get(account_id=user)

        # Retrieve the activity based on the provided activity_id
        activity = Activity.objects.select_related('school', 'logger', 'recipient', 'classroom').get(activity_id=details.get('activity_id'))

        # Check permissions
        permission_error = permission_checks.check_activity_permissions(account, activity)
        if permission_error:
            return permission_error
        
        # Serialize the activity data
        serializer = ActivitySerializer(activity).data

        return {"activity": serializer}

    except CustomUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}

    except Activity.DoesNotExist:
        # Handle case where the activity does not exist
        return {'error': 'An activity with the provided ID does not exist. Please check the activity details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}

    

@database_sync_to_async
def search_teacher_classes(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        # If the requesting user is looking for their own classes
        if details.get('teacher_id') == 'requesting_my_own_classes':
            classes = account.taught_classes.exclude(register_class=True)

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return {"error": "unauthorized access. you are not permitted to access classes of any teacher account with your role"}

            teacher = CustomUser.objects.get(account_id=details.get('teacher_id'))

            if teacher.role != 'TEACHER' or account.school != teacher.school:
                return {"error": "unauthorized access. you are not permitted to view classses of teacher accounts outside your own school"}

            classes = teacher.taught_classes

        serializer = TeacherClassesSerializer(classes, many=True)

        return {"classes": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def search_teacher_schedule_schedules(user, details):
    """
    Function to search and retrieve schedules for a specific teacher.

    This function performs the following steps:
    1. Determine if the user is requesting their own schedule or another teacher's schedule.
    2. Retrieve the teacher's account and validate their role.
    3. Verify the requester's permissions:
       - Teachers can request their own schedules.
       - Admins and Principals from the same school can access a teacher's schedule.
    4. Retrieve and serialize the teacher's schedules.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the account_id of the teacher.

    Returns:
        dict: A dictionary containing either the teacher schedules or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user or teacher with the provided account ID does not exist.
        TeacherSchedule.DoesNotExist: If the teacher does not have a schedule.
        Exception: For any other unexpected errors.

    Example:
        response = await search_teacher_schedule_schedules(request.user.account_id, {'account_id': 'T123'})
        if 'error' in response:
            # Handle error
        else:
            schedules = response['schedules']
            # Process schedules
    """
    try:
        # Check if the user is requesting their own schedule
        if details.get('account_id') == 'requesting_my_own_schedule':
            # Retrieve the teacher's account
            teacher = CustomUser.objects.get(account_id=user)

            # Ensure the user has the role of 'TEACHER'
            if teacher.role != 'TEACHER':
                return {"error": "Only teachers or admins and principals from the same school can make requests and access their schedules."}

        else:
            # Retrieve the account making the request
            account = CustomUser.objects.get(account_id=user)
            
            # Retrieve the teacher's account
            teacher = CustomUser.objects.get(account_id=details.get('account_id'))

            # Ensure the teacher's role and the requester's permissions
            if teacher.role != 'TEACHER' or account.school != teacher.school or account.role not in ['ADMIN', 'PRINCIPAL']:
                return {"error": "Only admins and principals from the same school can access a teacher's schedule."}

        # Retrieve the teacher's schedule
        teacher_schedule = TeacherSchedule.objects.get(teacher=teacher)
        schedules = teacher_schedule.schedules.all()

        # Serialize the schedules to return them in the response
        serializer = ScheduleSerializer(schedules, many=True)
        return {"schedules": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except TeacherSchedule.DoesNotExist:
        # Handle case where the teacher does not have a schedule
        return {'schedules': []}
    
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
        account = CustomUser.objects.get(account_id=user)
        
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
    
    except CustomUser.DoesNotExist:
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
        account = CustomUser.objects.get(account_id=user)
        
        # Ensure the specified role is valid
        if account.role not in ['ADMIN', 'PRINCIPAL', 'PARENT', 'TEACHER', 'STUDENT']:
            return {"error": "The specified account's role is invalid. please ensure you are attempting to access group schedules from an authorized account."}

        group_schedules = []

        if account.role in ['ADMIN', 'PRINCIPAL']:
            if details.get('account_id'):
                # Retrieve the student
                student = CustomUser.objects.get(account_id=details.get('account_id'))

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
            child = CustomUser.objects.get(account_id=details.get('account_id'))

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
            student = CustomUser.objects.get(account_id=details.get('account_id'))

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
    
    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Grade.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'the specified grade does not exist. Please check the grade details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_for_schedule_sessions(details):

    try:
        schedule = Schedule.objects.get(schedule_id=details.get('schedule_id'))
    
        sessions = schedule.sessions.all()
        serializer = SessoinsSerializer(sessions, many=True)
        
        return { "sessions" : serializer.data }
    
    except Schedule.DoesNotExist:
        return {"error" : "schedule with the provided ID does not exist"}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_month_attendance_records(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
 
        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can view the attendance records for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school, register_class=True)
        
        start_date, end_date = get_month_dates(details.get('month_name'))

        # Query for the Absent instances where absentes is True
        absents = Absent.objects.filter(Q(date__gte=start_date) & Q(date__lt=end_date) & Q(classroom=classroom) & Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for absent in absents:
            late = Late.objects.filter(date__date=absent.date.date(), classroom=classroom).first()
            record = {
                'date': absent.date.isoformat(),
                'absent_students': StudentAccountAttendanceRecordSerializer(absent.absent_students.all(), many=True).data,
                'late_students': StudentAccountAttendanceRecordSerializer(late.late_students.all(), many=True).data if late else [],
            }
            attendance_records.append(record)

        return {'records': attendance_records}
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

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
        account = CustomUser.objects.get(account_id=user)

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

    except CustomUser.DoesNotExist:
        # Handle case where the user or announcement does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_chat_room(user, details):
    """
    Search for an existing chat room between two users and return the requested user's details.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the details of the request, including:
            - 'account_id' (str): The account ID of the user to search for.

    Returns:
        dict: A dictionary containing the serialized requested user's data, a flag indicating if a chat room exists, the chat room ID if it exists, or an error message.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the requested user's account
        requested_user = CustomUser.objects.get(account_id=details.get('account_id'))
        
        # Check permissions
        permission_error = permission_checks.check_message_permissions(account, requested_user)
        if permission_error:
            return {'error': permission_error}
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=account, user_two=requested_user) | Q(user_one=requested_user, user_two=account)).first()
        
        chat_room_exists = bool(chat_room)

        # Serialize the requested user's data
        return {'user': ChatroomSerializer(requested_user).data, 'chat': chat_room_exists}

    except CustomUser.DoesNotExist:
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
        account = CustomUser.objects.get(account_id=user)
        requested_user = CustomUser.objects.get(account_id=details.get('account_id'))
        
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

    except CustomUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except ChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}
    
    except Exception as e:
        return {'error': str(e)}

