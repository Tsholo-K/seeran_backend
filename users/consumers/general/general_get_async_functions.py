# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q
from django.utils.translation import gettext as _

# models 
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from email_bans.models import EmailBan
from chats.models import ChatRoom

# serializers
from email_bans.serializers import EmailBansSerializer
from announcements.serializers import AnnouncementsSerializer
from chats.serializers import ChatSerializer

# mappings
from users.maps import role_specific_maps

# utility functions 
from users import utils as users_utilities


@database_sync_to_async
def fetch_security_information(user, role):
    serialized_user = users_utilities.get_account_and_security_details(user, role)
    
    # Return the retrieved security information
    return {'info': serialized_user}


@database_sync_to_async
def fetch_email_information(user):
    try:
        # Retrieve the user's email address and email ban details
        account = BaseUser.objects.values('email', 'email_ban_amount', 'email_banned').get(account_id=user)
        
        # Retrieve email ban records for the user's email address, ordered by the most recent ban first
        email_bans = EmailBan.objects.filter(email=account['email']).order_by('-banned_at')
        
        # Serialize the email ban records for easier consumption by the frontend or API
        serializer = EmailBansSerializer(email_bans, many=True)
    
        # Construct and return the response containing user information and email ban details
        return {'information': {'email_bans': serializer.data, 'strikes': account['email_ban_amount'], 'banned': account['email_banned']}}

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
def fetch_announcements(user, role):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Fetch announcements based on role
        if role == 'PARENT':
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.prefetch_related('children__school__announcements').get(account_id=user)

            # Collect all announcements from each child's school
            announcements = []
            for child in requesting_account.children.all():
                announcements.extend(child.school.announcements.all())

        else:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.prefetch_related('school__announcements').get(account_id=user)

            # Fetch announcements related to the user's school
            announcements = requesting_account.school.announcements.all()

        # Serialize the announcements
        serializer = AnnouncementsSerializer(announcements, many=True, context={'user': user})

        return {'announcements': serializer.data}
               
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
        return {'error': str(e)}

