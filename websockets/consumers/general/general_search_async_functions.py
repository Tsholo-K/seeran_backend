# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q
from django.core.cache import cache
from django.utils.translation import gettext as _

# models 
from accounts.models import BaseAccount
from email_address_bans.models import EmailAddressBan
from private_chat_rooms.models import PrivateChatRoom

# serializers
from accounts.serializers.general_serializers import DisplayAccountDetailsSerializer
from email_address_bans.serializers import EmailBanSerializer
from private_chat_room_messages.serializers import PrivateChatRoomMessageSerializer

# utility functions 
from accounts import utils as accounts_utilities

# checks
from accounts.checks import permission_checks


@database_sync_to_async
def search_email_ban(details):
    try:
        # Retrieve the email ban record from the database
        email_ban = EmailAddressBan.objects.get(ban_id=details.get('email_ban'))

        # Determine if a new OTP request can be made
        can_request = not cache.get(details.get('email') + 'email_revalidation_otp')
        
        # Serialize the email ban record
        serialized_email_ban = EmailBanSerializer(email_ban).data
        
        return {"email_ban": serialized_email_ban, "can_request": can_request}
        
    except EmailAddressBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while retrieving the email ban: {str(e)}'}


@database_sync_to_async
def search_chat_room(account, role, details):
    try:
        # Retrieve the account making the request
        # requesting_user = BaseAccount.objects.get(account_id=account)

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = accounts_utilities.get_account_and_permission_check_attr(account=account, role=role)

        # Retrieve the requested user's account
        requested_user = BaseAccount.objects.get(account_id=details.get('account'))

        # Build the queryset for the requested account with the necessary related fields.
        requested_account = accounts_utilities.get_account_and_permission_check_attr(account=details.get('account'), role=requested_user.role)
        
        # Check permissions
        permission_error = permission_checks.message(requesting_account, requested_account)
        if permission_error:
            return {'error': permission_error}
        
        # Check if a chat room exists between the two users
        chat_room = PrivateChatRoom.objects.filter(Q(participant_one=requesting_account, participant_two=requested_user) | Q(participant_one=requested_user, participant_two=requesting_account)).first()
        
        chat_room_exists = bool(chat_room)
        
        serializerd_user = DisplayAccountDetailsSerializer(requested_user).data

        # Serialize the requested user's data
        return {'user': serializerd_user, 'chat': chat_room_exists}

    except BaseAccount.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_chat_room_messages(user, details):
    try:
        # Retrieve the account making the request
        requesting_user = BaseAccount.objects.get(account_id=user)
        requested_user = BaseAccount.objects.get(account_id=details.get('account'))
        
        # Check if a chat room exists between the two users
        chat_room = PrivateChatRoom.objects.filter(Q(participant_one=requesting_user, participant_two=requested_user) | Q(participant_one=requested_user, participant_two=requesting_user)).select_related('participant_one', 'participant_two').first()
        
        if not chat_room:
            return {"not_found": 'No such chat room exists'}
        
        if details.get('cursor'):
            # Fetch messages before the cursor with a limit of 20
            messages = chat_room.messages.filter(timestamp__lt=details['cursor']).order_by('-timestamp')[:20]
        else:
            # Fetch the latest 20 messages
            messages = chat_room.messages.order_by('-timestamp')[:20]

        if not messages.exists():
            return {'messages': [], 'next_cursor': None, 'unread_messages': 0}

        # Convert messages to a list and reverse for correct ascending order
        messages = list(messages)[::-1]

        # Serialize the messages
        serialized_messages = PrivateChatRoomMessageSerializer(messages, many=True, context={'participant': user}).data
        
        # Determine the next cursor
        next_cursor = messages[0].timestamp.isoformat() if len(messages) > 19 else None

        # Mark unread messages as read and count them in one query
        unread_messages = chat_room.messages.filter(read_receipt=False).exclude(author=requesting_user)

        # Check if there are any messages that match the criteria
        unread_count = unread_messages.count()
        if unread_count > 0:
            # Mark the messages as read
            unread_messages.update(read_receipt=True)
            return {'messages': serialized_messages, 'next_cursor': next_cursor, 'unread_messages': unread_count, 'user': str(requested_user.account_id), 'chat': str(requesting_user.account_id)}
        
        else:
            # Handle the case where no messages need to be updated
            return {'messages': serialized_messages, 'next_cursor': next_cursor, 'unread_messages': 0}

    except BaseAccount.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        return {'error': str(e)}

