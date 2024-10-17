# channels
from channels.db import database_sync_to_async

# django
from django.db import models
from django.utils.translation import gettext as _

# models 
from accounts.models import BaseAccount
from chat_rooms.models import PrivateChatRoom
from email_address_bans.models import EmailAddressBan

# serializers
from chat_rooms.serializers import PrivateChatRoomsSerializer
from email_address_bans.serializers import EmailBansSerializer

# utility functions 
from accounts import utils as accounts_utilities


# Function to retrieve and return the security information of a user's account
@database_sync_to_async
def view_my_security_information(account, role):
    """
    Retrieves the security information for a specific user based on their role.

    Args:
        user (UUID or str): The account ID of the requesting user.
        role (str): The role of the user (e.g., 'ADMIN', 'TEACHER', 'STUDENT').

    Returns:
        dict: A dictionary containing the serialized user account and security details, or an error message.
    """
    # Call a utility function to fetch the account and security details for the user
    serialized_security_information = accounts_utilities.get_account_and_security_information(account, role)
    
    # Return the serialized data as part of the response
    return {'information': serialized_security_information}


# Function to retrieve and return the email address and ban status information for a user
@database_sync_to_async
def view_my_email_address_status_information(account):
    """
    Retrieves the email address, email ban amount, ban status, and historical ban details for a user.

    Args:
        user (UUID or str): The account ID of the requesting user.

    Returns:
        dict: A dictionary containing email ban details, strikes, and ban status, or an error message.
    """
    try:
        # Step 1: Retrieve the user's account, including email-related fields (email address, ban amount, and ban status)
        requesting_account = BaseAccount.objects.values('email_address', 'email_ban_amount', 'email_banned').get(account_id=account)
        
        # Step 2: Fetch email ban records associated with the user's email, ordered by the most recent ban
        email_bans = EmailAddressBan.objects.filter(banned_email_address=requesting_account['email_address']).order_by('-timestamp')
        
        # Step 3: Serialize the email ban records for structured API response or frontend consumption
        serialized_email_bans = EmailBansSerializer(email_bans, many=True).data
    
        # Step 4: Construct the final response, combining email bans, strikes, and ban status
        return {
            'information': {
                'email_bans': serialized_email_bans,            # List of previous email bans
                'strikes': requesting_account['email_ban_amount'],          # Number of strikes or bans the user has
                'banned': requesting_account['email_banned']                # Current ban status (True if banned)
            }
        }

    # Handle cases where the provided user account does not exist in the database
    except BaseAccount.DoesNotExist:
        return {'error': 'Could not process your request, an account with the provided credentials does not exist. Please review the account details and try again.'}
    
    # Catch-all exception handler for any other unexpected errors
    except Exception as e:
        return {'error': str(e)}   # Return a generic error message


# Function to retrieve and return chat rooms where the user is a participant, ordered by latest activity
@database_sync_to_async
def view_chat_rooms(account):
    """
    Retrieves all chat rooms where the user is involved, ordered by the latest message timestamp.

    Args:
        user (UUID or str): The account ID of the requesting user.

    Returns:
        dict: A dictionary containing serialized chat rooms or an error message.
    """
    try:
        # Step 1: Retrieve the requesting user's account details using their account ID
        requesting_user = BaseAccount.objects.get(account_id=account)
        
        # Step 2: Fetch chat rooms where the user is involved either as participant_one or participant_two.
        # Order the results by the latest message timestamp (if available), otherwise by the room's creation timestamp.
        chat_rooms = PrivateChatRoom.objects.select_related('participant_one', 'participant_two').filter(
            models.Q(participant_one=requesting_user) | models.Q(participant_two=requesting_user)
        ).order_by('latest_message_timestamp')

        # Step 3: Serialize the chat rooms using a serializer to prepare the data for the API or frontend
        serialized_chat_rooms = PrivateChatRoomsSerializer(chat_rooms, many=True, context={'account': account}).data
        
        # Step 4: Return the serialized chat rooms as part of the response
        return {'chat_rooms': serialized_chat_rooms}

    # Handle cases where the user account does not exist in the database
    except BaseAccount.DoesNotExist:
        return {'error': 'Could not process your request, an account with the provided credentials does not exist. Please review the account details and try again.'}
    
    # Catch-all exception handler for any unexpected errors
    except Exception as e:
        return {'error': f'An unexpected error occurred while fetching chat rooms: {str(e)}'}


# @database_sync_to_async
# def view_school_announcements(user, role):
#     try:
#         if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
#             return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

#         # Get the appropriate model for the requesting user's role from the mapping.
#         Model = role_specific_maps.account_access_control_mapping[role]

#         # Fetch announcements based on role
#         if role == 'PARENT':
#             # Build the queryset for the requesting account with the necessary related fields.
#             requesting_account = Model.objects.prefetch_related('children__school__announcements').get(account_id=user)

#             # Collect all announcements from each child's school
#             announcements = []
#             for child in requesting_account.children.all():
#                 announcements.extend(child.school.announcements.all())

#         else:
#             # Build the queryset for the requesting account with the necessary related fields.
#             requesting_account = Model.objects.prefetch_related('school__announcements').get(account_id=user)

#             # Fetch announcements related to the user's school
#             announcements = requesting_account.school.announcements.all()

#         # Serialize the announcements
#         serializer = AnnouncementsSerializer(announcements, many=True, context={'user': user})

#         return {'announcements': serializer.data}
               
#     except Principal.DoesNotExist:
#         # Handle the case where the requested principal account does not exist.
#         return {'error': 'Could not process your request, A principal account with the provided credentials does not exist, please check the account details and try again'}
                   
#     except Admin.DoesNotExist:
#         # Handle the case where the requested admin account does not exist.
#         return {'error': 'An admin account with the provided credentials does not exist, please check the account details and try again'}
               
#     except Teacher.DoesNotExist:
#         # Handle the case where the requested teacher account does not exist.
#         return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
                   
#     except Student.DoesNotExist:
#         # Handle the case where the requested student account does not exist.
#         return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}
               
#     except Parent.DoesNotExist:
#         # Handle the case where the requested parent account does not exist.
#         return {'error': 'A parent account with the provided credentials does not exist, please check the account details and try again'}

#     except Exception as e:
#         return {'error': str(e)}

