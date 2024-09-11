# python 
import time

# channels
from channels.db import database_sync_to_async

# django
from django.db import  transaction
from django.core.cache import cache
from django.utils.translation import gettext as _

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from access_tokens.models import AccessToken
from users.models import BaseUser
from chats.models import ChatRoom, ChatRoomMessage

# serializers
from users.serializers.general_serializers import BareAccountDetailsSerializer
from chats.serializers import ChatRoomMessageSerializer

# checks
from users.checks import permission_checks

# utility functions 
from users import utils as users_utilities


@database_sync_to_async
def text(user, role, details):
    try:
        # Validate users
        if user == details.get('account'):
            return {"error": "validation error. you can not send a text message to yourself, it violates database constraints and is therefore not allowed."}

        # Retrieve the user making the request
        requesting_user = BaseUser.objects.get(account_id=user)
        
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_attr(user, role)

        # Retrieve the requested user's account
        requested_user = BaseUser.objects.get(account_id=details.get('account'))

        # Retrieve the requested users account and related school in a single query using select_related
        requested_account = users_utilities.get_account_and_attr(details.get('account'), role)

        # Check permissions
        permission_error = permission_checks.check_message_permissions(requesting_account, requested_account)
        if permission_error:
            return {'error': permission_error}

        # Retrieve or create the chat room
        chat_room, created = ChatRoom.objects.get_or_create(user_one=requesting_user if requesting_user.pk < requested_user.pk else requested_user, user_two=requested_user if requesting_user.pk < requested_user.pk else requesting_user, defaults={'user_one': requesting_user, 'user_two': requested_user})

        with transaction.atomic():
            # Retrieve the last message in the chat room
            last_message = ChatRoomMessage.objects.filter(chat_room=chat_room).order_by('-timestamp').first()
            # Update the last message's 'last' field if it's from the same sender
            if last_message and last_message.sender == requesting_user:
                last_message.last = False
                last_message.save()

            # Create the new message
            new_message = ChatRoomMessage.objects.create(sender=requesting_user, content=details.get('message'), chat_room=chat_room)

            # Update the chat room's latest message timestamp
            chat_room.latest_message_timestamp = new_message.timestamp
            chat_room.save()

        # Serialize the new message
        serializer = ChatRoomMessageSerializer(new_message, context={'user': user})
        message_data = serializer.data

        return {'message': message_data, 'sender': BareAccountDetailsSerializer(requesting_user).data, 'reciever':  BareAccountDetailsSerializer(requested_user).data}

    except BaseUser.DoesNotExist:
        return {'error': 'User account not found. Please verify the account details.'}

    except Exception as e:
        return {'error': str(e)}


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
    
