# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q
from django.utils.translation import gettext as _

# simple jwt

# models 
from users.models import CustomUser
from email_bans.models import EmailBan
from announcements.models import Announcement
from chats.models import ChatRoom

# serializers
from email_bans.serializers import EmailBansSerializer
from announcements.serializers import AnnouncementsSerializer
from chats.serializers import ChatSerializer

# utility functions 

# checks


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

