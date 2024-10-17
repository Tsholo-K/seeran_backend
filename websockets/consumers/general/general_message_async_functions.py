# channels
from channels.db import database_sync_to_async

# django
from django.db import  transaction
from django.utils.translation import gettext as _
from django.utils import timezone

# models 
from accounts.models import BaseAccount
from chat_rooms.models import PrivateChatRoom
from chat_room_messages.models import  PrivateMessage

# serializers
from accounts.serializers.general_serializers import BareAccountDetailsSerializer
from chat_room_messages.serializers import PrivateChatRoomMessageSerializer

# checks
from accounts.checks import permission_checks

# utility functions 
from accounts import utils as accounts_utilities


@database_sync_to_async
def message_private(account, role, details):
    try:
        # Validate users
        if account == details.get('account'):
            return {"error": "validation error. you can not send a text message to yourself, it violates database constraints and is therefore not allowed."}

        # Retrieve the requested user's account
        requesting_user = BaseAccount.objects.get(account_id=account)

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_permission_check_attr(account, role)

        # Retrieve the requested user's account
        requested_user = BaseAccount.objects.get(account_id=details.get('account'))

        # Retrieve the requested users account and related school in a single query using select_related
        requested_account = accounts_utilities.get_account_and_permission_check_attr(details.get('account'), requested_user.role)

        # Check permissions
        permission_error = permission_checks.message(requesting_account, requested_account)
        if permission_error:
            return {'error': permission_error}

        with transaction.atomic():
            timestamp = timezone.now()

            # Retrieve or create the chat room
            private_chat_room, created = PrivateChatRoom.objects.get_or_create(participant_one=requesting_user if requesting_user.id < requested_user.id else requested_user, participant_two=requested_user if requesting_user.id < requested_user.id else requesting_user, defaults={'participant_one': requesting_user, 'participant_two': requested_user, 'latest_message_timestamp': timestamp})
            
            if created:
                # Create the new message
                new_private_chat_room_message = PrivateMessage.objects.create(author=requesting_user, message_content=details.get('message'), chat_room=private_chat_room, timestamp=timestamp)
            
            else:
                # Retrieve the last message in the chat room
                private_chat_room_last_message = private_chat_room.messages.order_by('-timestamp').first()

                # Update the last message's 'last' field if it's from the same sender
                if private_chat_room_last_message and private_chat_room_last_message.author == requesting_user:
                    private_chat_room_last_message.last_message = False
                    private_chat_room_last_message.save(update_fields=['last_message'])

                # Create the new message
                new_private_chat_room_message = PrivateMessage.objects.create(author=requesting_user, message_content=details.get('message'), chat_room=private_chat_room)

        # Serialize the new message
        serialized_message = PrivateChatRoomMessageSerializer(new_private_chat_room_message, context={'participant': account}).data

        serialized_author = BareAccountDetailsSerializer(requesting_user).data
        serialized_recipient = BareAccountDetailsSerializer(requested_user).data

        return {'message': serialized_message, 'author': serialized_author, 'recipient': serialized_recipient}

    except BaseAccount.DoesNotExist:
        return {'error': 'Could not process your request, an account with the provided credentials does not exist. Please review the account details and try again.'}

    except Exception as e:
        return {'error': str(e)}

    
