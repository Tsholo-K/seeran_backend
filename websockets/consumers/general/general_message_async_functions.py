# channels
from channels.db import database_sync_to_async

# django
from django.db import  transaction
from django.utils.translation import gettext as _
from django.utils import timezone

# models 
from accounts.models import BaseAccount
from private_chat_rooms.models import PrivateChatRoom, PrivateChatRoomMembership
from private_chat_room_messages.models import PrivateMessage

# serializers
from accounts.serializers.general_serializers import BareAccountDetailsSerializer
from private_chat_room_messages.serializers import PrivateChatRoomMessageSerializer

# checks
from accounts.checks import permission_checks

# utility functions 
from accounts import utils as accounts_utilities


@database_sync_to_async
def message_private(account, role, details):
    try:
        # Validate users
        if account == details.get('account'):
            return {"error": "Validation error: You cannot send a message to yourself. This violates database constraints and is not allowed."}

        # Retrieve the requesting user's account and related attributes
        requesting_account = accounts_utilities.get_account_and_permission_check_attr(account, role)

        # Retrieve the requested user's account and related attributes
        requested_user = BaseAccount.objects.get(account_id=details.get('account'))
        requested_account = accounts_utilities.get_account_and_permission_check_attr(details.get('account'), requested_user.role)

        # Perform permission checks
        permission_error = permission_checks.message(requesting_account, requested_account)
        if permission_error:
            return {'error': permission_error}

        with transaction.atomic():
            timestamp = timezone.now()

            # Retrieve or create the chat room with the participants
            chat_room = PrivateChatRoom.objects.filter(
                participants=requesting_account
            ).filter(participants=requested_user).first()

            if not chat_room:
                # Create the new chat room and add participants
                chat_room = PrivateChatRoom.objects.create(latest_message_timestamp=timestamp)
                PrivateChatRoomMembership.objects.bulk_create([
                    PrivateChatRoomMembership(chat_room=chat_room, participant=requesting_account),
                    PrivateChatRoomMembership(chat_room=chat_room, participant=requested_user)
                ])

            # Check if the latest message in the chat room is from the same sender and update it
            last_message = chat_room.messages.order_by('-timestamp').first()
            if last_message and last_message.author == requesting_account:
                last_message.last_message = False
                last_message.save(update_fields=['last_message'])

            # Create a new message in the chat room
            new_message = PrivateMessage.objects.create(
                author=requesting_account,
                message_content=details.get('message'),
                chat_room=chat_room,
                timestamp=timestamp
            )

        # Serialize the new message
        serialized_message = PrivateChatRoomMessageSerializer(new_message, context={'participant': account}).data

        # Serialize the author and recipient
        serialized_author = BareAccountDetailsSerializer(requesting_account).data
        serialized_recipient = BareAccountDetailsSerializer(requested_user).data

        return {'message': serialized_message, 'author': serialized_author, 'recipient': serialized_recipient}

    except BaseAccount.DoesNotExist:
        return {'error': 'An account with the provided credentials does not exist. Please review the account details and try again.'}

    except Exception as e:
        return {'error': str(e)}


    
