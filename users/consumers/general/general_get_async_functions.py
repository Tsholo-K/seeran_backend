# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q
from django.utils.translation import gettext as _

# simple jwt

# models 
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from email_bans.models import EmailBan
from announcements.models import Announcement
from chats.models import ChatRoom

# serializers
from email_bans.serializers import EmailBansSerializer
from announcements.serializers import AnnouncementsSerializer
from chats.serializers import ChatSerializer

# utility functions 

# mappings
from users.maps import role_specific_maps


@database_sync_to_async
def fetch_security_information(user, role):
    try:
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model, Serializer = role_specific_maps.account_model_and_security_serializer_mapping[role]

        # Retrieve the user's security settings from the database
        account = Model.objects.get(account_id=user)

        serialized_user = Serializer(account).data
        
        # Return the retrieved security information
        return {'info': serialized_user}
               
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
        account = BaseUser.objects.values('email', 'email_ban_amount', 'email_banned').get(account_id=user)
        
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

    except BaseUser.DoesNotExist:
        # Handle the case where no user is found with the provided account ID
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any unexpected errors that occur during the process
        return {'error': f'An unexpected error occurred while retrieving user information: {str(e)}'}


@database_sync_to_async
def fetch_chats(user):
    try:
        # Retrieve the user account
        requesting_account = BaseUser.objects.get(account_id=user)
        
        # Fetch chat rooms where the user is involved and order by latest message timestamp
        chat_rooms = ChatRoom.objects.filter(Q(user_one=requesting_account) | Q(user_two=requesting_account)).order_by('-latest_message_timestamp')

        # Serialize chat room data
        serialized_chats = ChatSerializer(chat_rooms, many=True, context={'user': user}).data
        
        return {'chats': serialized_chats}

    except BaseUser.DoesNotExist:
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
        account = BaseUser.objects.get(account_id=user)

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

    except BaseUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except Exception as e:
        return {'error': str(e)}

