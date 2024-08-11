# python 
from decouple import config
import base64
import time
# httpx
import httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import  transaction
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.contrib.auth.hashers import check_password

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from auth_tokens.models import AccessToken
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
from email_bans.serializers import EmailBansSerializer, EmailBanSerializer
from timetables.serializers import SessoinsSerializer, ScheduleSerializer
from timetables.serializers import GroupScheduleSerializer
from announcements.serializers import AnnouncementsSerializer, AnnouncementSerializer
from chats.serializers import ChatRoomMessageSerializer, ChatSerializer
from classes.serializers import TeacherClassesSerializer, ClassSerializer
from activities.serializers import ActivityCreationSerializer, ActivitiesSerializer, ActivitySerializer

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email
from attendances.utility_functions import get_month_dates

# checks
from users.checks import permission_checks


@database_sync_to_async
def fetch_my_security_information(user):
    """
    Retrieves security-related information for a given user.

    This function fetches the multi-factor authentication (MFA) status and event email settings
    for the user identified by `user`. The retrieved information includes whether MFA is enabled
    and the settings for event-related emails.

    Args:
        user (str): The account ID of the user whose security information is to be fetched.

    Returns:
        dict: A dictionary containing:
            - 'multifactor_authentication': A boolean indicating whether multi-factor authentication is enabled for the user.
            - 'event_emails': A boolean indicating whether event-related emails are enabled for the user.
            - 'error': A string containing an error message if an exception is raised.

    Raises:
        CustomUser.DoesNotExist: If no user is found with the provided account ID.
        Exception: For any other errors that occur during the process.

    Example:
        response = await fetch_my_security_information(request.user.account_id)
        if 'error' in response:
            # Handle error, e.g., display error message to the user
        else:
            security_info = response
            # Process security information
    """
    try:
        # Retrieve the user's security settings from the database
        account = CustomUser.objects.values('multifactor_authentication', 'event_emails').get(account_id=user)
        
        # Return the retrieved security information
        return {
            'multifactor_authentication': account['multifactor_authentication'],  # MFA status
            'event_emails': account['event_emails']  # Event email settings
        }

    except CustomUser.DoesNotExist:
        # Handle the case where no user is found with the provided account ID
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors and return a descriptive error message
        return {'error': str(e)}


@database_sync_to_async
def fetch_my_email_information(user):
    """
    Retrieves user information and associated email ban records.

    This function fetches specific fields for the user identified by `user`. 
    It retrieves the user's email address, the number of email bans, 
    and whether the email is currently banned. It also fetches and serializes
    all email ban records associated with the user's email address.

    Args:
        user (str): The account ID of the user whose information is to be retrieved.

    Returns:
        dict: A dictionary containing:
            - 'information': A dictionary with the following keys:
                - 'email_bans': A list of serialized email ban records associated with the user's email address.
                - 'strikes': The number of email bans associated with the user's email.
                - 'banned': A boolean indicating whether the user's email is currently banned.
            - 'error': A string containing an error message if an exception is raised.
    
    Raises:
        CustomUser.DoesNotExist: If no user is found with the provided account ID.
        Exception: For any other errors that occur during the process.
    """
    try:
        # Retrieve the user's email address and email ban details
        account = CustomUser.objects.values('email', 'email_ban_amount', 'email_banned').get(account_id=user)
        
        # Retrieve email ban records for the user's email address, ordered by the most recent ban first
        email_bans = EmailBan.objects.filter(email=account['email']).order_by('-banned_at')
        
        # Serialize the email ban records for easier consumption by the frontend or API
        serializer = EmailBansSerializer(email_bans, many=True)
    
        # Construct and return the response containing user information and email ban details
        return {
            'information': {
                'email_bans': serializer.data,  # Serialized data for email bans
                'strikes': account['email_ban_amount'],  # Number of times the email has been banned
                'banned': account['email_banned']  # Whether the email is currently banned
            }
        }

    except CustomUser.DoesNotExist:
        # Handle the case where no user is found with the provided account ID
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any unexpected errors that occur during the process
        return {'error': f'An unexpected error occurred while retrieving user information: {str(e)}'}


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
def validate_email_revalidation(user, details):
    """
    Validates whether a user can appeal an email ban and handles OTP limits.

    This function checks if the email ban can be appealed based on the user's account email and
    current status of the email ban. It also updates the email ban status if OTP limits are exceeded.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing:
            - 'email_ban_id': The ID of the email ban to be validated.

    Returns:
        dict: A dictionary containing:
            - 'user': The user account information if the email ban can be appealed.
            - 'error': A string containing an error message if the appeal is not possible.
            - 'denied': A string containing a denial message if OTP limits are exceeded.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        EmailBan.DoesNotExist: If the email ban with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await validate_email_revalidation('user123', {'email_ban_id': 123})
        if 'error' in response:
            # Handle error
        elif 'denied' in response:
            # Handle denial
        else:
            user_info = response['user']
            # Process user information
    """
    try:
        # Retrieve the user account
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the email ban record
        email_ban = EmailBan.objects.get(ban_id=details.get('email_ban_id'))
        
        # Check if the email in the ban matches the user's email
        if email_ban.email != account.email:
            return {"error": "Invalid request: the banned email differs from the account email."}

        # Check the status and appeal possibility of the email ban
        if email_ban.status == 'APPEALED':
            return {"error": "The email ban has already been appealed."}

        if not email_ban.can_appeal:
            return {"error": "This email ban cannot be appealed."}
        
        # Check if the maximum OTP sends have been reached
        if email_ban.otp_send >= 3:
            email_ban.can_appeal = False
            email_ban.status = 'BANNED'
            email_ban.save()
            return {"denied": "Maximum number of OTP sends reached. The email is now permanently banned."}
        
        return {'user': account}

    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided ID does not exist. Please check the account details and try again.'}

    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while validating email revalidation: {str(e)}'}


@database_sync_to_async
def update_email_ban_otp_sends(email_ban_id):
    """
    Updates the OTP sends count for a specific email ban and sets the ban status to 'PENDING'.

    This function increments the count of OTP sends for the specified email ban and updates the status
    to 'PENDING' if it is not already set to that status.

    Args:
        email_ban_id (int): The ID of the email ban to be updated.

    Returns:
        dict: A dictionary containing:
            - 'message': A message indicating that a new OTP has been sent.
            - 'error': A string containing an error message if an exception is raised.

    Raises:
        EmailBan.DoesNotExist: If the email ban with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await update_email_ban_otp_sends(123)
        if 'error' in response:
            # Handle error
        else:
            message = response['message']
            # Process OTP update
    """
    try:
        # Retrieve the email ban record
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        # Increment the OTP sends count and update status
        email_ban.otp_send += 1
        if email_ban.status != 'PENDING':
            email_ban.status = 'PENDING'
        email_ban.save()
        
        return {"message": "A new OTP has been sent to your email address."}

    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while updating OTP sends: {str(e)}'}


@database_sync_to_async
def verify_email_revalidate_otp(user, details):
    """
    Verifies the OTP for email revalidation and updates the email ban status accordingly.

    This function checks if the provided OTP is correct and matches the OTP stored in cache.
    If the OTP is valid, it updates the email ban status to 'APPEALED' and unbans the email. 
    If the OTP is invalid or the maximum number of attempts is reached, it updates the ban status as needed.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing:
            - 'email_ban_id': The ID of the email ban.
            - 'otp': The OTP provided by the user.

    Returns:
        dict: A dictionary containing:
            - 'message': A message indicating the success of email revalidation or a denial message if OTP limits are exceeded.
            - 'error': A string containing an error message if OTP verification fails.
            - 'denied': A string containing a denial message if OTP limits are exceeded.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        EmailBan.DoesNotExist: If the email ban with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await verify_email_revalidate_otp('user123', {'email_ban_id': 123, 'otp': '456789'})
        if 'error' in response:
            # Handle error
        elif 'denied' in response:
            # Handle denial
        else:
            message = response['message']
            # Process successful OTP verification
    """
    try:
        # Retrieve the user account
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the email ban record
        email_ban = EmailBan.objects.get(ban_id=details.get('email_ban_id'))
        
        # Retrieve the OTP from cache
        hashed_otp = cache.get(account.email + 'email_revalidation_otp')
        if not hashed_otp:
            cache.delete(account.email + 'email_revalidation_attempts')
            return {"error": "OTP expired. Please request a new OTP."}

        # Verify the provided OTP
        if verify_user_otp(user_otp=details.get('otp'), stored_hashed_otp_and_salt=hashed_otp):
            # OTP is valid, update ban status and user account
            email_ban.status = 'APPEALED'
            account.email_banned = False
            account.save()
            email_ban.save()

            return {"message": "Email successfully revalidated. The email ban has been lifted.", 'status': email_ban.status.title()}

        else:
            # OTP is invalid, update remaining attempts and handle expiration
            attempts = cache.get(account.email + 'email_revalidation_attempts', 3)
            attempts -= 1
            
            if attempts <= 0:
                cache.delete(account.email + 'email_revalidation_otp')
                cache.delete(account.email + 'email_revalidation_attempts')
                
                if email_ban.otp_send >= 3:
                    email_ban.can_appeal = False
                    email_ban.status = 'BANNED'
                    email_ban.save()
                
                return {"denied": "Maximum OTP verification attempts exceeded. The email ban remains in place."}
            
            cache.set(account.email + 'email_revalidation_attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"Revalidation error: incorrect OTP. {attempts} attempts remaining."}

    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided ID does not exist. Please check the account details and try again.'}

    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while verifying OTP: {str(e)}'}


@database_sync_to_async
def fetch_chats(user):
    """
    Retrieves chat rooms associated with the user.

    This function fetches all chat rooms where the user is either `user_one` or `user_two`.

    Args:
        user (str): The account ID of the user whose chat rooms are to be fetched.

    Returns:
        dict: A dictionary containing:
            - 'chats': Serialized data of chat rooms associated with the user.
            - 'error': A string containing an error message if an exception is raised.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await fetch_chats('user123')
        if 'error' in response:
            # Handle error
        else:
            chat_rooms = response['chats']
            # Process chat rooms
    """
    try:
        # Retrieve the user account
        account = CustomUser.objects.get(account_id=user)
        
        # Fetch chat rooms where the user is involved and order by latest message timestamp
        chat_rooms = ChatRoom.objects.filter(Q(user_one=account) | Q(user_two=account)).order_by('-latest_message_timestamp')

        # Serialize chat room data
        serializer = ChatSerializer(chat_rooms, many=True, context={'user': user})
        
        return {'chats': serializer.data}

    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided ID does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while fetching chat rooms: {str(e)}'}


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

    try:
        account = CustomUser.objects.get(account_id=user)

        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school)
        
        # Check permissions
        permission_error = permission_checks.check_class_permissions(account, classroom)
        if permission_error:
            return permission_error

        serializer = ClassSerializer(classroom)

        return {"class": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}
    
    except Exception as e:
        return { 'error': str(e) }


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
        
        # Retrieve the requested user's account
        classroom = Classroom.objects.get(class_id=details.get('class_id'))
        
        if account.school != classroom.school:
            return {"error": "unauthorized access. you are not permitted to view information about classses outside your own school"}

        # Serialize the requested user's account ID
        serializer = BySerializer(instance=student).data

        # Serialize the activities 
        activities = Activity.objects.filter(classroom=classroom, recipient=student)
        serializer2 = ActivitiesSerializer(activities, many=True).data

        return {"user": serializer, 'activities' : serializer2}

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
            classes = account.taught_classes.all().exclude(register_class=True)

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return {"error": "unauthorized access. you are not permitted to access classes of any teacher account with your role"}

            teacher = CustomUser.objects.get(account_id=details.get('teacher_id'))

            if teacher.role != 'TEACHER' or account.school != teacher.school:
                return {"error": "unauthorized access. you are not permitted to view classses of teacher accounts outside your own school"}

            classes = teacher.taught_classes.all()

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
def submit_absentes(user, details):

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

        today = timezone.localdate()

        if Absent.objects.filter(date__date=today, classroom=classroom).exists():
            return {'error': 'attendance register for this class has already been subimitted today.. can not resubmit'}

        with transaction.atomic():
            register = Absent.objects.create(submitted_by=account, classroom=classroom)
            if details.get('students'):
                register.absentes = True
                for student in details.get('students').split(', '):
                    register.absent_students.add(CustomUser.objects.get(account_id=student))

            register.save()
        
        return { 'message': 'attendance register successfully taken for today'}

    except CustomUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def submit_late_arrivals(user, details):

    try:
        if not details.get('students'):
            return {"error" : 'invalid request.. no students provided.. at least one student is needed to be marked as late'}

        account = CustomUser.objects.get(account_id=user)

        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can view the attendance records for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school, register_class=True)

        today = timezone.localdate()

        absentes = Absent.objects.filter(date__date=today, classroom=classroom).first()
        if not absentes:
            return {'error': 'attendance register for this class has not been submitted today.. can not submit late arrivals before the attendance register'}

        if absentes and not absentes.absent_students.exists():
            return {'error': 'attendance register for this class has all students present or marked as late for today.. can not submit late arrivals when all students are accounted for'}

        register = Late.objects.filter(date__date=today, classroom=classroom).first()
        
        with transaction.atomic():
            if not register:
                register = Late.objects.create(submitted_by=account, classroom=classroom)
                
            for student in details.get('students').split(', '):
                student = CustomUser.objects.get(account_id=student)
                absentes.absent_students.remove(student)
                register.late_students.add(student)

            absentes.save()
            register.save()

        return { 'message': 'students marked as late, attendance register successfully updated'}
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

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
def log_activity(user, details):
    """
    Log an activity for a student by an authorized user (Principal, Admin, Teacher).

    Args:
        user (str): The account ID of the user logging the activity.
        details (dict): A dictionary containing the details of the activity. It should include:
            - 'recipient' (str): The account ID of the student for whom the activity is being logged.
            - Additional fields required by the ActivityCreationSerializer.

    Returns:
        dict: A dictionary containing a success message if the activity was logged successfully,
              or an error message if there was an issue.
    """
    try:
        # Retrieve the user account and the student account using select_related to minimize database hits
        account = CustomUser.objects.select_related('school').get(account_id=user)
        student = CustomUser.objects.select_related('school').get(account_id=details.get('recipient'))

        # Ensure the account has a valid role to log activities
        if account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": "unauthorized request. you do not have sufficient permissions to log activities."}

        # Ensure the student belongs to the same school and has the 'STUDENT' role
        if account.school != student.school or student.role != 'STUDENT':
            return {"error": "unauthorized request. the provided student account is either not a student or does not belong to your school. Please check the account details and try again."}

        # If the account is a teacher, ensure they are teaching the student and the teacher of hte class
        if account.role == 'TEACHER':
            # Retrieve the classroom
            classroom = Classroom.objects.get(class_id=details.get('class_id'))
            
            if account.school != classroom.school:
                return {"error": "unauthorized access. you are not permitted to access information about classses outside your own school or those you do not teacher"}

            if classroom not in account.taught_classes.all() or not account.taught_classes.filter(students=student).exists():
                return {"error": "unauthorized access. you can only log activities for classrooms and students you teach."}
  
            details['classroom'] = classroom.pk

        # Prepare the data for serialization
        details['recipient'] = student.pk
        details['logger'] = account.pk
        details['school'] = account.school.pk

        # Initialize the serializer with the prepared data
        serializer = ActivityCreationSerializer(data=details)

        # Validate the serializer data and save the activity within an atomic transaction
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

            return {'message': 'activity successfully logged. the activity is now available to everyone with access to the student\'s data.'}

        # Return validation errors if the serializer is not valid
        return {"error": serializer.errors}

    except CustomUser.DoesNotExist:
        # Handle case where the user or student account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except Exception as e:
        # Handle any other unexpected exceptions
        return {'error': str(e)}

    

@database_sync_to_async
def update_email(user, details, access_token):
    
    try:
        if not validate_user_email(details.get('new_email')):
            return {'error': 'Invalid email format'}
        
        if CustomUser.objects.filter(email=details.get('new_email')).exists():
            return {"error": "an account with the provided email address already exists"}

        account = CustomUser.objects.get(account_id=user)
        
        if details.get('new_email') == account.email:
            return {"error": "cannot set current email as new email"}
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP, action forrbiden"}
    
        EmailBan.objects.filter(email=account.email).delete()
        
        account.email = details.get('new_email')
        account.email_ban_amount = 0
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "email changed successfully"}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def update_password(user, details, access_token):
    
    try:
        account = CustomUser.objects.get(account_id=user)

        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired.. taking you back to password verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP.. action forrbiden"}
    
        validate_password(details.get('new_password'))
        
        account.set_password(details.get('new_password'))
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "password changed successfully"}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}
    
    except ValidationError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def verify_email(details):

    try:
        if not validate_user_email(details.get('email')):
            return {'error': 'Invalid email format'}
        
        account = CustomUser.objects.get(email=details.get('email'))
        
        # check if users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned.. request denied"}
        
        return {'user' : account}
    
    except CustomUser.DoesNotExist:
        return {'error': 'invalid email address'}

    except ValidationError:
        return {"error": "invalid email address"}
        
    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_password(user, details):
    
    try:
        account = CustomUser.objects.get(account_id=user)
        
        # check if the users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned, request denied"}
            
        # Validate the password
        if not check_password(details.get('password'), account.password):
            return {"error": "invalid password, please try again"}
        
        return {"user" : account}
       
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_otp(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        stored_hashed_otp_and_salt = cache.get(account.email + 'account_otp')

        if not stored_hashed_otp_and_salt:
            cache.delete(account.email + 'account_otp_attempts')
            return {"denied": "OTP expired.. please generate a new one"}

        if verify_user_otp(user_otp=details.get('otp'), stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            # OTP is verified, prompt the user to set their password
            cache.delete(account.email)
            
            authorization_otp, hashed_authorization_otp, salt = generate_otp()
            cache.set(account.email + 'authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "OTP verified successfully..", "authorization_otp" : authorization_otp}
        
        else:

            attempts = cache.get(account.email + 'account_otp_attempts', 3)
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            
            if attempts <= 0:
                cache.delete(account.email + 'account_otp')
                cache.delete(account.email + 'account_otp_attempts')
                
                return {"denied": "maximum OTP verification attempts exceeded.."}
            
            cache.set(account.email + 'account_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"incorrect OTP.. {attempts} attempts remaining"}
       
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
 
    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def update_multi_factor_authentication(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        if account.email_banned:
            return { "error" : "your email has been banned"}
    
        account.multifactor_authentication = details.get('toggle')
        account.save()
        
        return {'message': 'Multifactor authentication {} successfully'.format('enabled' if details.get('toggle') else 'disabled')}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def log_out(access_token):
         
    try:
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
        
        return {"message": "logged you out successful"}
    
    except TokenError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def fetch_announcements(user):
    """
    Fetch announcements for a user based on their role and associated schools.

    This function performs the following steps:
    1. Fetch the user account making the request.
    2. Validate the user's role to ensure it is authorized to access announcements.
    3. Retrieve announcements based on the user's role:
       - For parents, fetch announcements related to their children's schools.
       - For other roles (Student, Admin, Principal), fetch announcements related to the user's school.
    4. Serialize the announcements and return them.

    Args:
        user (CustomUser): The user object making the request.

    Returns:
        dict: A dictionary containing serialized announcements or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user does not exist in the database.
        Exception: For any other unexpected errors.

    Example:
        response = await search_announcements(request.user)
        if 'error' in response:
            # Handle error
        else:
            announcements = response['announcements']
            # Process announcements
    """
    try:
        # Fetch the user account making the request
        account = CustomUser.objects.get(account_id=user)

        # Validate user role
        if account.role not in ['PARENT', 'STUDENT', 'TEACHER', 'ADMIN', 'PRINCIPAL']:
            return {"error": "the specified account's role is invalid. Please ensure you are attempting to access announcements from an authorized account."}

        # Fetch announcements based on role
        if account.role == 'PARENT':
            # Fetch announcements related to the schools of the user's children
            children_schools = account.children.values_list('school', flat=True)
            announcements = Announcement.objects.filter(school__in=children_schools)

        else:
            # Fetch announcements related to the user's school
            announcements = Announcement.objects.filter(school=account.school)

        # Serialize the announcements
        serializer = AnnouncementsSerializer(announcements, many=True, context={'user': user})
        return {'announcements': serializer.data}

    except CustomUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except Exception as e:
        return {'error': str(e)}


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
def text(user, details):
    """
    Handle sending a text message. 
    
    This function performs the following steps:
    1. Retrieves the user making the request and the requested user's account.
    2. Checks if the user has the necessary permissions to send the message.
    3. Retrieves or creates a chat room between the two users.
    4. Checks the last message and updates its 'last' field if necessary.
    5. Creates and saves a new message in the chat room.
    6. Serializes the new message and returns it.
    7. Includes the recipient's account ID in the response for further processing.

    Args:
        user (str): The account ID of the user sending the message.
        details (dict): A dictionary containing the details of the message, including:
            - 'account_id' (str): The account ID of the user to whom the message is sent.
            - 'message' (str): The content of the message.

    Returns:
        dict: A dictionary containing the serialized message data and the recipient's account ID or an error message.
    """
    try:
        # Retrieve the user making the request
        account = CustomUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        requested_user = CustomUser.objects.get(account_id=details.get('account_id'))
        
        # Check permissions
        permission_error = permission_checks.check_message_permissions(account, requested_user)
        if permission_error:
            return {'error': permission_error}

        # Retrieve or create the chat room
        chat_room, created = ChatRoom.objects.get_or_create(user_one=account if account.pk < requested_user.pk else requested_user, user_two=requested_user if account.pk < requested_user.pk else account, defaults={'user_one': account, 'user_two': requested_user})

        with transaction.atomic():
            # Retrieve the last message in the chat room
            last_message = ChatRoomMessage.objects.filter(chat_room=chat_room).order_by('-timestamp').first()
            # Update the last message's 'last' field if it's from the same sender
            if last_message and last_message.sender == account:
                last_message.last = False
                last_message.save()

            # Create the new message
            new_message = ChatRoomMessage.objects.create(sender=account, content=details.get('message'), chat_room=chat_room)

            # Update the chat room's latest message timestamp
            chat_room.latest_message_timestamp = new_message.timestamp
            chat_room.save()

        # Serialize the new message
        serializer = ChatRoomMessageSerializer(new_message, context={'user': user})
        message_data = serializer.data

        return {'message': message_data, 'sender': { 'name' : account.name.title() , 'surname' : account.surname.title(), 'image' : '/default-user-image.svg', 'id' : account.account_id}, 'reciever': { 'name' : requested_user.name.title() , 'surname' : requested_user.surname.title(), 'image' : '/default-user-image.svg', 'id' : requested_user.account_id}}

    except CustomUser.DoesNotExist:
        return {'error': 'User account not found. Please verify the account details.'}
    
    except Exception as e:
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
        serializer = ChatroomSerializer(requested_user)
        
        return {'user': serializer.data, 'chat': chat_room_exists}

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
        # Retrieve the requested user's account
        requested_user = CustomUser.objects.get(account_id=details.get('account_id'))
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=account, user_two=requested_user) | Q(user_one=requested_user, user_two=account)).first()
        
        if not chat_room:
            return {"not_found": 'no such chat room exists'}

        # Retrieve the cursor from the request
        cursor = details.get('cursor')
        if cursor:
            # Fetch messages with a timestamp less than the cursor (if cursor is present)
            messages = ChatRoomMessage.objects.filter(chat_room=chat_room, timestamp__lt=cursor).order_by('-timestamp')[:20]
        else:
            # Fetch the latest messages if no cursor is provided
            messages = ChatRoomMessage.objects.filter(chat_room=chat_room).order_by('-timestamp')[:20]

        # Slice and then reverse the order to get the correct ascending order
        messages = list(messages)[::-1]

        # Serialize the messages
        serializer = ChatRoomMessageSerializer(messages, many=True, context={'user': user})
        
        # Determine the next cursor
        if len(messages) > 19:
            next_cursor = messages[0].timestamp.isoformat()
        else:
            next_cursor = None

        # Query for messages that need to be marked as read
        messages_to_update = ChatRoomMessage.objects.filter(chat_room=chat_room, read_receipt=False).exclude(sender=account)

        # Check if there are any messages that match the criteria
        if messages_to_update.exists():

            # Mark the messages as read
            messages_to_update.update(read_receipt=True)
            return {'messages': serializer.data, 'next_cursor': next_cursor, 'user': requested_user.account_id, 'chat': account.account_id}
        
        else:
            # Handle the case where no messages need to be updated (optional)
            return {'messages': serializer.data, 'next_cursor': next_cursor}

    except CustomUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except ChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def mark_messages_as_read(user, details):
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        requested_user = CustomUser.objects.get(account_id=details.get('account_id'))
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=account, user_two=requested_user) | Q(user_one=requested_user, user_two=account)).first()

        if chat_room:

            # Query for messages that need to be marked as read
            messages_to_update = ChatRoomMessage.objects.filter(chat_room=chat_room, read_receipt=False).exclude(sender=account)

            # Check if there are any messages that match the criteria
            if messages_to_update.exists():

                # Mark the messages as read
                messages_to_update.update(read_receipt=True)
                return {"read": True, 'user': requested_user.account_id, 'chat': account.account_id}
            
            else:
                # Handle the case where no messages need to be updated (optional)
                return {"read": True}
        
        return {"error": 'no such chat room exists'}

    except CustomUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
        
    except ChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_attendance_register(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can submit the attendance register for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), register_class=True, school=account.school)
        
        # Get today's date
        today = timezone.localdate()
            
        # Check if an Absent instance exists for today and the given class
        attendance = Absent.objects.filter(date__date=today, classroom=classroom).first()

        if attendance:
            students = attendance.absent_students.all()
            attendance_register_taken = True

        else:
            students = classroom.students.all()
            attendance_register_taken = False

        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data, "attendance_register_taken" : attendance_register_taken}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


async def send_account_confirmation_email(user):
    
    try:
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"
        
        email_data = {
            "from": "seeran grades <accounts@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
            "subject": "Account Creation Confirmation",
            "template": "account creation confirmation",
        }
        
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post( mailgun_api_url, headers=headers, data=email_data )
            
        if response.status_code == 200:
            return {"message": f"an account confirmation email has been sent to the users email address"}
            
        else:
            return {"error": "failed to send OTP to users email address"}
    
    except Exception as e:
        return {"error": str(e)}


async def send_one_time_pin_email(user, reason):
    
    try:
        otp, hashed_otp, salt = generate_otp()

        # Define your Mailgun API URL
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
            "subject": "One Time Passcode",
            "template": "one-time passcode",
            "v:onetimecode": otp,
            "v:otpcodereason": reason
        }

        # Define your headers
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send the email via Mailgun
        async with httpx.AsyncClient() as client:
            response = await client.post( mailgun_api_url, headers=headers, data=email_data )

        if response.status_code == 200:
                
            # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
            # this is cached to our redis database for faster retrieval when we verify the otp
            cache.set(user.email + 'account_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "a new OTP has been sent to your email address"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}

        else:
            return {"error": "failed to send OTP to your  email address"}
    
    except Exception as e:
        return {"error": str(e)}


async def send_email_revalidation_one_time_pin_email(user):
    
    try:
        otp, hashed_otp, salt = generate_otp()

        # Define your Mailgun API URL
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
            "subject": "One Time Passcode",
            "template": "one-time passcode",
            "v:onetimecode": otp,
            "v:otpcodereason": 'This OTP was generated for your account in response to your email revalidation request'
        }

        # Define your headers
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send the email via Mailgun
        async with httpx.AsyncClient() as client:
            response = await client.post( mailgun_api_url, headers=headers, data=email_data )

        if response.status_code == 200:
                
            # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
            # this is cached to our redis database for faster retrieval when we verify the otp
            cache.set(user.email + 'email_revalidation_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "email sent"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}
        
        else:
            return {"error": "failed to send OTP to your  email address"}

    except Exception as e:
        return {"error": str(e)}
            
